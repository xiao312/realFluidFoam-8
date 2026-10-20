#pragma once
#include "SrkPhase.h"
#include "cantera/oneD/Flow1D.h"

namespace liang {
// Steady diagnostic: preserve the phase's partial-molar API and change only
// the flow energy equation. No SDK patch or transient-state restart is needed.
class TotalEnthalpyFlow : public Cantera::Flow1D {
public:
    TotalEnthalpyFlow(std::shared_ptr<Cantera::Solution> solution, bool pure)
        : Cantera::Flow1D(solution,"flow"), pureSpecies_(pure) {}

protected:
    void evalEnergy(double* x,double* residual,int* diagonal,double inverseTime,
                    size_t first,size_t last) override {
        if(!m_isFree || m_twoPointControl || m_do_radiation)
            throw std::runtime_error("Total-enthalpy diagnostic supports adiabatic free flames only");
        // Retain stock boundary and fixed-temperature equations.
        Cantera::Flow1D::evalEnergy(x,residual,diagonal,inverseTime,first,last);
        const size_t begin=std::max<size_t>(first,1);
        const size_t end=std::min(last,m_points-2);
        if(begin>end)return;
        const size_t base=begin-1;
        std::vector<double> mixtureH(end-begin+3),faceFlux(end-begin+2),speciesH(m_nsp);
        for(size_t j=begin-1;j<=end+1;j++) {
            setGas(x,j);
            mixtureH[j-base]=m_thermo->enthalpy_mass();
        }
        for(size_t j=begin-1;j<=end;j++) {
            setGasAtMidpoint(x,j);
            m_thermo->getPartialMolarEnthalpies(speciesH.data());
            const auto* srk=dynamic_cast<const SrkPhase*>(m_thermo);
            if(pureSpecies_ && srk && srk->stage>=3) {
                const auto& mixture=srk->state();
                for(size_t k=0;k<m_nsp;k++) {
                    const auto pure=evaluate(m_thermo->temperature(),m_press,{1.},
                                             {srk->parameters[k]},srk->smoothedAlpha,srk->signedAlpha);
                    speciesH[k]+=pure.h-mixture.hb[k];
                }
            }
            const double massFlux=.5*(rho_u(x,j)+rho_u(x,j+1));
            faceFlux[j-base]=massFlux*(massFlux>=0?mixtureH[j-base]:mixtureH[j+1-base])
                -m_tcon[j]*(T(x,j+1)-T(x,j))/m_dz[j];
            for(size_t k=0;k<m_nsp;k++)
                faceFlux[j-base]+=m_flux(k,j)*speciesH[k]/m_wt[k];
        }
        for(size_t j=begin;j<=end;j++) {
            if(!m_do_energy[j])continue;
            const double width=.5*(m_dz[j-1]+m_dz[j]);
            residual[index(Cantera::c_offset_T,j)]=
                -(faceFlux[j-base]-faceFlux[j-1-base])/(width*m_rho[j]*m_cp[j])
                -inverseTime*(T(x,j)-T_prev(j));
            diagonal[index(Cantera::c_offset_T,j)]=1;
        }
    }
private:
    bool pureSpecies_;
};
}
