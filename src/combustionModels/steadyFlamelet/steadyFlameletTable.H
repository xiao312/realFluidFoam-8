#ifndef steadyFlameletTable_H
#define steadyFlameletTable_H

#include <string>
#include <vector>

// Strict one-dimensional physical table; independent of OpenFOAM and FGM.
namespace forgeSteady
{
struct State
{
    double temperature, heatRelease;
    std::vector<double> y;
};
class Table
{
    std::vector<double> z_;
    std::vector<State> states_;
    std::vector<std::vector<double>> elements_;
    void validate() const;
public:
    std::vector<std::string> species, elementNames;
    std::string chiDefinition;
    double pressure, chi, oxidizerTemperature, fuelTemperature;
    explicit Table(const std::string& path);
    State lookup(double z) const;
    std::size_t size() const { return z_.size(); }
};
}
#endif
