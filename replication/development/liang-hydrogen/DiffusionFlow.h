#pragma once
#include "cantera/oneD/Flow1D.h"
#include <stdexcept>
#include <utility>

namespace hydrogen {
// PREMIX 2.5b MDIFV uses Y_face for the correction velocity. Stock Cantera 3.2
// uses Y_left. Preserve all ordinary coefficients, gradients and energy methods.
// Source identity and applicability limits are recorded in the transport audit.
template<class EnergyFlow>
class MidpointCorrectionFlow : public EnergyFlow {
public:
    using EnergyFlow::EnergyFlow;
protected:
    void updateDiffFluxes(const double* x,size_t first,size_t last) override {
        if(this->m_do_multicomponent || this->m_do_soret
           || this->m_fluxGradientBasis!=Cantera::ThermoBasis::molar)
            throw std::runtime_error("Midpoint control requires mixture-averaged molar flux without Soret");
        for(size_t j=first;j<last;j++) {
            double correction=0;
            const double dz=this->z(j+1)-this->z(j);
            for(size_t k=0;k<this->m_nsp;k++) {
                this->m_flux(k,j)=this->m_diff[k+this->m_nsp*j]
                    *(this->X(x,k,j)-this->X(x,k,j+1))/dz;
                correction-=this->m_flux(k,j);
            }
            for(size_t k=0;k<this->m_nsp;k++)
                this->m_flux(k,j)+=correction*.5*(this->Y(x,k,j)+this->Y(x,k,j+1));
        }
    }
};

template<class EnergyFlow,class... Args>
std::shared_ptr<Cantera::Flow1D> makeFlow(bool midpoint,Args&&... args) {
    if(midpoint)
        return std::make_shared<MidpointCorrectionFlow<EnergyFlow>>(std::forward<Args>(args)...);
    return std::make_shared<EnergyFlow>(std::forward<Args>(args)...);
}
}
