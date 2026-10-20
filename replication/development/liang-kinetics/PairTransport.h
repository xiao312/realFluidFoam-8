#pragma once
#include "cantera/transport/MixTransport.h"
#include "cantera/thermo/ThermoPhase.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace kinetics_control {
struct DiffusionPair {
    std::string first,second;
    std::array<double,4> coefficients;
};
inline std::vector<DiffusionPair> readPairs(const std::string& path) {
    if(path=="-")return {};
    std::ifstream file(path);
    if(!file)throw std::runtime_error("Missing author pair table");
    std::vector<DiffusionPair> result;std::set<std::pair<std::string,std::string>> seen;
    std::string line;
    while(std::getline(file,line)) {
        if(line.find_first_not_of(" \t\r")==std::string::npos)continue;
        std::istringstream row(line);DiffusionPair pair;std::string extra;
        if(!(row>>pair.first>>pair.second))throw std::runtime_error("Malformed pair");
        for(auto& value:pair.coefficients)
            if(!(row>>value) || !std::isfinite(value))throw std::runtime_error("Invalid pair coefficient");
        if(row>>extra)throw std::runtime_error("Unexpected pair column");
        const auto names=std::minmax(pair.first,pair.second);
        if(!seen.emplace(names.first,names.second).second)
            throw std::runtime_error("Duplicate unordered diffusion pair");
        result.push_back(pair);
    }
    if(result.empty())throw std::runtime_error("Supplied pair table is empty");
    return result;
}
class PairTransport : public Cantera::MixTransport {
public:
    std::vector<DiffusionPair> pairs;
    std::vector<std::pair<size_t,size_t>> indices;
    size_t pairUpdates=0;
    void init(Cantera::ThermoPhase* gas,int mode=0) override {
        indices.clear();
        for(const auto& pair:pairs) {
            const size_t i=gas->speciesIndex(pair.first),j=gas->speciesIndex(pair.second);
            if(i>=gas->nSpecies() || j>=gas->nSpecies())
                throw std::runtime_error("Author pair contains an absent species");
            indices.emplace_back(i,j);
        }
        Cantera::MixTransport::init(gas,mode);
    }
protected:
    void updateDiff_T() override {
        Cantera::GasTransport::updateDiff_T();
        const double t=std::log(m_temp);
        for(size_t k=0;k<pairs.size();k++) {
            const auto& d=pairs[k].coefficients;
            const double pd=101325e-4*std::exp(d[0]+t*(d[1]+t*(d[2]+t*d[3])));
            if(!(pd>0 && std::isfinite(pd)))throw std::runtime_error("Invalid author diffusion value");
            const auto [i,j]=indices[k];m_bdiff(i,j)=m_bdiff(j,i)=pd;
        }
        pairUpdates++;
    }
};
}
