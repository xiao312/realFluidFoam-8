#pragma once
#include "SrkPhase.h"
#include "cantera/oneD/Flow1D.h"

namespace liang {
// Diagnostic mixture-averaged closure: add the composition contribution to
// X_k grad(log fugacity_k) at constant T,p. It is not an identified Liang model.
class NonidealDiffusionFlow : public Cantera::Flow1D {
public:
    explicit NonidealDiffusionFlow(std::shared_ptr<Cantera::Solution> solution)
        : Cantera::Flow1D(solution,"flow") {}

protected:
    void updateDiffFluxes(const double* x,size_t first,size_t last) override {
        Cantera::Flow1D::updateDiffFluxes(x,first,last);
        const auto* srk=dynamic_cast<const SrkPhase*>(m_thermo);
        if(!srk || srk->stage<2)return; // Exact stock-flow ideal control.
        if(m_do_multicomponent || m_do_soret || m_fluxGradientBasis!=Cantera::ThermoBasis::molar)
            throw std::runtime_error("Nonideal driving diagnostic requires molar mixture diffusion without Soret");
        std::vector<double> left(m_nsp),right(m_nsp),midpoint(m_nsp),extra(m_nsp);
        for(size_t j=first;j<last;j++) {
            setGas(x,j);m_thermo->getMoleFractions(left.data());
            setGas(x,j+1);m_thermo->getMoleFractions(right.data());
            const double temperature=.5*(T(x,j)+T(x,j+1));
            // Identical T,p on both sides: no thermal-diffusion term.
            const auto a=evaluate(temperature,m_press,left,srk->parameters,srk->smoothedAlpha);
            const auto b=evaluate(temperature,m_press,right,srk->parameters,srk->smoothedAlpha);
            setGasAtMidpoint(x,j);m_thermo->getMoleFractions(midpoint.data());
            double total=0;
            for(size_t k=0;k<m_nsp;k++) {
                // m_diff already contains rho * W_k/Wbar * D_k at this face.
                extra[k]=-m_diff[k+m_nsp*j]*midpoint[k]*(b.lnphi[k]-a.lnphi[k])/m_dz[j];
                if(!std::isfinite(extra[k]))throw std::runtime_error("Nonfinite nonideal diffusion flux");
                total+=extra[k];
            }
            for(size_t k=0;k<m_nsp;k++)m_flux(k,j)+=extra[k]-Y(x,k,j)*total;
        }
    }
};
}
