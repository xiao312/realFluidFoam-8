#pragma once
#include "../cantera-liang/StagedTransport.h"
#include "CollisionPairs.h"
#include <array>
#include <fstream>
#include <limits>
#include <map>

namespace hydrogen {
struct Pair {
    std::string first,second;
    std::array<double,4> d;
};
inline std::vector<Pair> readPairs(const std::string& path) {
    std::ifstream file(path);
    if(!file)throw std::runtime_error("Missing explicit pairs.txt (empty means LJ control)");
    std::vector<Pair> rows;Pair p;
    while(file>>p.first>>p.second>>p.d[0]>>p.d[1]>>p.d[2]>>p.d[3])rows.push_back(p);
    if(!file.eof())throw std::runtime_error("Malformed diffusion pair table");
    if(!rows.empty() && rows.size()!=10)throw std::runtime_error("Expected ten pairs or empty LJ control");
    return rows;
}
class Transport : public liang::StagedTransport {
public:
    std::vector<Pair> pairs;
    std::vector<CollisionPair> collisionPairs;
    size_t pairUpdates=0;
    size_t thermalCalls=0,authorCollisionCalls=0,fallbackCollisionCalls=0;
    double thermalMinimumT=std::numeric_limits<double>::infinity();
    double thermalMaximumT=0;
    void init(Cantera::ThermoPhase* gas,int mode=0) override {
        liang::StagedTransport::init(gas,mode);
        collisionLookup.clear();
        if(collisionPairs.empty())return; // Old no-Soret inputs remain valid.
        std::set<std::pair<std::string,std::string>> binaryKeys,collisionKeys;
        for(const auto& pair:pairs)
            if(!binaryKeys.insert(pairKey(pair.first,pair.second)).second)
                throw std::runtime_error("Duplicate author binary pair");
        for(size_t row=0;row<collisionPairs.size();row++) {
            const auto& pair=collisionPairs[row];
            collisionKeys.insert(pairKey(pair.first,pair.second));
            size_t first=gas->speciesIndex(pair.first),second=gas->speciesIndex(pair.second);
            if(first>=m_nsp || second>=m_nsp)
                throw std::runtime_error("Unknown collision-pair species");
            collisionLookup[{std::min(first,second),std::max(first,second)}]=row;
        }
        if(binaryKeys!=collisionKeys || collisionLookup.size()!=collisionPairs.size())
            throw std::runtime_error("Author binary and collision pair inventories differ");
    }
    void getThermalDiffCoeffs(double* output) override {
        const double temperature=m_thermo->temperature();
        thermalCalls++;
        thermalMinimumT=std::min(thermalMinimumT,temperature);
        thermalMaximumT=std::max(thermalMaximumT,temperature);
        liang::StagedTransport::getThermalDiffCoeffs(output);
    }
protected:
    std::map<std::pair<size_t,size_t>,size_t> collisionLookup;
    liang::CollisionRatios manualCollisionRatios(size_t first,size_t second,double temperature) override {
        const auto found=collisionLookup.find({std::min(first,second),std::max(first,second)});
        if(found==collisionLookup.end()) {
            fallbackCollisionCalls++;
            return liang::StagedTransport::manualCollisionRatios(first,second,temperature);
        }
        authorCollisionCalls++;
        return evaluateCollisionPair(collisionPairs[found->second],temperature);
    }
    void updateDiff_T() override {
        Cantera::GasTransport::updateDiff_T();
        // Burke/Wang CHEMKIN extension: ln(D [cm2/s] at 1 atm) is cubic
        // in ln(T/K). Cantera stores P[Pa]*D[m2/s] in m_bdiff.
        // All three mixture-averaged APIs and the Takahashi path consume it.
        const double t=std::log(m_temp);
        for(const auto& p:pairs) {
            const size_t i=m_thermo->speciesIndex(p.first),j=m_thermo->speciesIndex(p.second);
            if(i>=m_nsp || j>=m_nsp)throw std::runtime_error("Unknown diffusion pair species");
            const double pd=101325.*1e-4*std::exp(p.d[0]+t*(p.d[1]+t*(p.d[2]+t*p.d[3])));
            if(!(pd>0 && std::isfinite(pd)))throw std::runtime_error("Invalid author pair diffusivity");
            m_bdiff(i,j)=m_bdiff(j,i)=pd;
        }
        pairUpdates++;
    }
};
}
