#include "steadyFlameletTable.H"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <set>
#include <stdexcept>

namespace forgeSteady
{
namespace
{
void require(bool condition, const std::string& message)
{
    if (!condition) throw std::runtime_error("steadyFlamelet table: " + message);
}
void key(std::istream& stream, const char* expected)
{
    std::string actual;
    require(bool(stream >> actual) && actual == expected, std::string("expected '") + expected + "'");
}
double number(std::istream& stream)
{
    double value;
    require(bool(stream >> value) && std::isfinite(value), "nonfinite or missing number");
    return value;
}
std::size_t count(std::istream& stream, std::size_t low, std::size_t high)
{
    const double value = number(stream);
    require(value >= low && value <= high && value == std::floor(value), "invalid array count");
    return std::size_t(value);
}
void names(std::istream& stream, std::vector<std::string>& values)
{
    std::set<std::string> unique;
    for (std::string& name : values)
        require(bool(stream >> name) && unique.insert(name).second, "missing or duplicate name");
}
}

Table::Table(const std::string& path)
{
    std::ifstream stream(path.c_str());
    require(bool(stream), "cannot open " + path);
    key(stream, "FORGE_STEADY_FLAMELET"); require(number(stream) == 1, "unsupported version");
    key(stream, "pressure-pa"); pressure = number(stream);
    key(stream, "chi-definition"); stream >> chiDefinition;
    key(stream, "chi-value-s-1"); chi = number(stream);
    key(stream, "oxidizer-temperature-k"); oxidizerTemperature = number(stream);
    key(stream, "fuel-temperature-k"); fuelTemperature = number(stream);
    require(pressure > 0 && chi > 0 && oxidizerTemperature > 0 && fuelTemperature > 0, "nonpositive condition");
    require(chiDefinition == "maximum" || chiDefinition == "stoichiometric", "unknown chi definition");
    key(stream, "species"); species.resize(count(stream, 2, 256)); names(stream, species);
    key(stream, "elements"); elementNames.resize(count(stream, 1, 32)); names(stream, elementNames);
    key(stream, "element-mass-coefficients");
    elements_.resize(elementNames.size(), std::vector<double>(species.size()));
    for (auto& row : elements_) for (double& value : row)
    {
        value = number(stream); require(value >= 0 && value <= 1, "invalid element coefficient");
    }
    key(stream, "points"); const std::size_t points = count(stream, 2, 200000);
    z_.resize(points); states_.resize(points); key(stream, "data");
    for (std::size_t i=0; i<points; ++i)
    {
        z_[i] = number(stream);
        State& state = states_[i]; state.temperature = number(stream); state.heatRelease = number(stream);
        state.y.resize(species.size()); for (double& value : state.y) value = number(stream);
    }
    key(stream, "end"); std::string trailing; require(!(stream >> trailing), "unexpected trailing token");
    validate();
}

void Table::validate() const
{
    const double limit = 1e-8;
    require(z_.front() == 0 && z_.back() == 1, "Z endpoints must be exactly0/1");
    const auto oxygen = std::find(species.begin(), species.end(), "O2");
    const auto methane = std::find(species.begin(), species.end(), "CH4");
    require(oxygen != species.end() && methane != species.end(), "pure O2/CH4 endpoints require both species");
    for (std::size_t s=0; s<species.size(); ++s)
    {
        double sum=0; for (const auto& element : elements_) sum += element[s];
        require(std::abs(sum-1) <= limit, "element coefficients do not sum to one for " + species[s]);
        require(std::abs(states_.front().y[s]-(species[s]=="O2" ? 1.0 : 0.0)) <= limit, "oxidizer is not pure O2");
        require(std::abs(states_.back().y[s]-(species[s]=="CH4" ? 1.0 : 0.0)) <= limit, "fuel is not pure CH4");
    }
    require(std::abs(states_.front().temperature-oxidizerTemperature) <= 1e-8 &&
            std::abs(states_.back().temperature-fuelTemperature) <= 1e-8, "endpoint temperature differs");
    for (std::size_t i=0; i<states_.size(); ++i)
    {
        require(i == 0 || z_[i] > z_[i-1], "Z must be strictly increasing");
        require(states_[i].temperature > 0, "nonpositive temperature");
        double sum=0;
        for (double value : states_[i].y)
        {
            require(value >= 0 && value <= 1+limit, "negative or excessive Y at row " + std::to_string(i));
            sum += value;
        }
        require(std::abs(sum-1) <= limit, "species sum fails at row " + std::to_string(i));
        for (const auto& element : elements_)
        {
            double actual=0, oxygen=0, fuel=0;
            for (std::size_t s=0; s<species.size(); ++s)
            {
                actual += states_[i].y[s]*element[s];
                oxygen += states_.front().y[s]*element[s];
                fuel += states_.back().y[s]*element[s];
            }
            require(std::abs(actual-((1-z_[i])*oxygen+z_[i]*fuel)) <= limit,
                "element balance fails at row " + std::to_string(i));
        }
    }
}

double Table::elementCoordinateDifference(double raw, double used) const
{
    require(std::isfinite(raw) && std::isfinite(used), "nonfinite element-audit coordinate");
    double worst=0;
    for (const auto& element : elements_)
    {
        double oxygen=0, fuel=0;
        for (std::size_t s=0; s<species.size(); ++s)
        {
            oxygen += states_.front().y[s]*element[s];
            fuel += states_.back().y[s]*element[s];
        }
        worst=std::max(worst, std::abs((used-raw)*(fuel-oxygen)));
    }
    return worst;
}

State Table::lookup(double z) const
{
    require(std::isfinite(z) && z >= 0 && z <= 1, "Z outside [0,1]; no clipping");
    if (z == 1) return states_.back();
    const std::size_t hi = std::upper_bound(z_.begin(), z_.end(), z)-z_.begin();
    const std::size_t lo = hi-1;
    const double weight=(z-z_[lo])/(z_[hi]-z_[lo]);
    State result; result.y.resize(species.size());
    result.temperature=(1-weight)*states_[lo].temperature+weight*states_[hi].temperature;
    result.heatRelease=(1-weight)*states_[lo].heatRelease+weight*states_[hi].heatRelease;
    for (std::size_t s=0; s<species.size(); ++s)
        result.y[s]=(1-weight)*states_[lo].y[s]+weight*states_[hi].y[s];
    return result;
}
}
