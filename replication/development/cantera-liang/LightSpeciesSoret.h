#pragma once
#include <array>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace liang {
// Published CHEMKIN light-species equation, evaluated directly.
// The archived TRANFIT sign is opposite; this explicitly follows the manual.
// Fixed zero-dipole collision fits use log(T / effective well depth [K]).
// These are not Cantera 3.2's degree-eight collision fits.
struct CollisionRatios { double a,b,c; };

inline CollisionRatios lightSpeciesCollisionRatios(double logReducedTemperature) {
    constexpr std::array<std::array<double,7>,3> coefficients{{
        {{1.106910525,-.007065517161,-.01671975393,.01188708609,
          .0007569367323,-.001313998345,.0001720853282}},
        {{1.199673577,-.1140928763,-.002147636665,.02512965407,
          -.003030372973,-.001445009039,.0002492954809}},
        {{.8386993788,.04748325276,.03250097527,-.01625859588,
          -.002260153363,.001844922811,-.0002115417788}}
    }};
    if(!std::isfinite(logReducedTemperature))
        throw std::runtime_error("Nonfinite reduced Soret temperature");
    std::array<double,3> value{};
    for(size_t k=0;k<3;k++) {
        value[k]=coefficients[k][6];
        for(int n=5;n>=0;n--)value[k]=coefficients[k][n]+logReducedTemperature*value[k];
    }
    return {value[0],value[1],value[2]};
}

inline double lightSpeciesPairFactor(const CollisionRatios& c,double firstWeight,
                                    double secondWeight) {
    const double denominator=c.a*(16*c.a-12*c.b+55);
    if(!(denominator>0 && firstWeight>0 && secondWeight>0) ||
       !std::isfinite(denominator+c.c+firstWeight+secondWeight))
        throw std::runtime_error("Invalid light-species Soret pair");
    return 7.5*(2*c.a+5)*(6*c.c-5)/denominator
           *(firstWeight-secondWeight)/(firstWeight+secondWeight);
}

// Output kg/(m s), consumed as -D^T grad(log T) by Flow1D.
// Caller supplies selected-stage Dmix and physical density. No second rho factor.
inline std::vector<double> projectLightSpeciesSoret(
        double density,double meanWeight,const std::vector<double>& weights,
        const std::vector<double>& x,const std::vector<double>& y,
        const std::vector<double>& diffusion,const std::vector<double>& theta) {
    const size_t count=weights.size();
    if(!(density>0 && meanWeight>0) || x.size()!=count || y.size()!=count ||
       diffusion.size()!=count || theta.size()!=count)
        throw std::runtime_error("Invalid light-species Soret state");
    std::vector<double> result(count);double sum=0;
    for(size_t k=0;k<count;k++) {
        // theta already contains X_k: absent species require no division by X_k.
        result[k]=density*diffusion[k]*weights[k]/meanWeight*theta[k];
        if(!std::isfinite(result[k]))throw std::runtime_error("Nonfinite thermal coefficient");
        sum+=result[k];
    }
    for(size_t k=0;k<count;k++)result[k]-=y[k]*sum;
    return result;
}
}
