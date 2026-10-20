#pragma once
#include "../cantera-liang/StagedTransport.h"
#include <array>
#include <fstream>

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
    size_t pairUpdates=0;
protected:
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
