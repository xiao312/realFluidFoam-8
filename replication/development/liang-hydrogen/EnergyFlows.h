#pragma once
#include "../cantera-liang/SrkPhase.h"
#include "cantera/oneD/Flow1D.h"

namespace hydrogen {
// Match Flow1D's species-advection stencil. The steady free-flame mass flux is
// constant; only conductive and species-enthalpy fluxes use dual-cell divergence.
class EnthalpyFlow : public Cantera::Flow1D {
public:
    EnthalpyFlow(std::shared_ptr<Cantera::Solution> sol,bool pure)
        : Cantera::Flow1D(sol,"flow"),pure_(pure) {}
protected:
    void evalEnergy(double* x,double* residual,int* diagonal,double inverseTime,
                    size_t first,size_t last) override {
        if(!m_isFree || m_twoPointControl || m_do_radiation)
            throw std::runtime_error("Enthalpy diagnostic requires adiabatic free flow");
        Cantera::Flow1D::evalEnergy(x,residual,diagonal,inverseTime,first,last);
        const size_t begin=std::max<size_t>(first,1),end=std::min(last,m_points-2);
        if(begin>end)return;
        const size_t base=begin-1;
        std::vector<double> h(end-begin+3),flux(end-begin+2),hk(m_nsp);
        for(size_t j=base;j<=end+1;j++) {
            setGas(x,j);h[j-base]=m_thermo->enthalpy_mass();
        }
        for(size_t j=base;j<=end;j++) {
            setGasAtMidpoint(x,j);m_thermo->getPartialMolarEnthalpies(hk.data());
            const auto* srk=dynamic_cast<const liang::SrkPhase*>(m_thermo);
            if(pure_ && srk && srk->stage>=3) {
                const auto& mixture=srk->state();
                for(size_t k=0;k<m_nsp;k++) {
                    const auto pure=liang::evaluate(m_thermo->temperature(),m_press,{1.},
                                                   {srk->parameters[k]},srk->smoothedAlpha);
                    hk[k]+=pure.h-mixture.hb[k];
                }
            }
            flux[j-base]=-m_tcon[j]*(T(x,j+1)-T(x,j))/m_dz[j];
            for(size_t k=0;k<m_nsp;k++)flux[j-base]+=m_flux(k,j)*hk[k]/m_wt[k];
        }
        for(size_t j=begin;j<=end;j++) {
            if(!m_do_energy[j])continue;
            const size_t up=u(x,j)>0?j:j+1;
            const double dh=(h[up-base]-h[up-base-1])/m_dz[up-1];
            const double diffusion=2*(flux[j-base]-flux[j-base-1])/(m_dz[j-1]+m_dz[j]);
            residual[index(Cantera::c_offset_T,j)]=
                -(rho_u(x,j)*dh+diffusion)/(m_rho[j]*m_cp[j])
                -inverseTime*(T(x,j)-T_prev(j));
            diagonal[index(Cantera::c_offset_T,j)]=1;
        }
    }
private:
    bool pure_;
};

// Deliberate pure-species temperature approximation discussed in Liang's ref.8:
// h_k=h_k^ideal+departure(pure k); Cp=sum(Y_k Cp_k^pure).
// It is not a replacement for thermodynamic partial molar properties.
class PureTemperatureFlow : public Cantera::Flow1D {
public:
    explicit PureTemperatureFlow(std::shared_ptr<Cantera::Solution> sol)
        : Cantera::Flow1D(sol,"flow") {}
protected:
    void evalEnergy(double* x,double* residual,int* diagonal,double inverseTime,
                    size_t first,size_t last) override {
        if(!m_isFree || m_twoPointControl || m_do_radiation)
            throw std::runtime_error("Pure-temperature diagnostic requires adiabatic free flow");
        const size_t begin=first>0?first-1:0,end=std::min(last+1,m_points-1);
        std::vector<double> savedCp(end-begin+1),savedH((end-begin+1)*m_nsp),h0(m_nsp),cp0(m_nsp);
        const auto* srk=dynamic_cast<const liang::SrkPhase*>(m_thermo);
        for(size_t j=begin;j<=end;j++) {
            savedCp[j-begin]=m_cp[j];setGas(x,j);
            m_thermo->getEnthalpy_RT_ref(h0.data());m_thermo->getCp_R_ref(cp0.data());
            double cp=0;
            for(size_t k=0;k<m_nsp;k++) {
                savedH[(j-begin)*m_nsp+k]=m_hk(k,j);
                double hk=liang::R*T(x,j)*h0[k],ck=liang::R*cp0[k];
                if(srk && srk->stage>=3) {
                    const auto pure=liang::evaluate(T(x,j),m_press,{1.},{srk->parameters[k]},srk->smoothedAlpha);
                    hk+=pure.h;ck+=pure.cp;
                }
                m_hk(k,j)=hk;cp+=Y(x,k,j)*ck/m_wt[k];
            }
            if(!(cp>0))throw std::runtime_error("Nonpositive pure-mixture Cp");
            m_cp[j]=cp;
        }
        Cantera::Flow1D::evalEnergy(x,residual,diagonal,inverseTime,first,last);
        for(size_t j=begin;j<=end;j++) {
            m_cp[j]=savedCp[j-begin];
            for(size_t k=0;k<m_nsp;k++)m_hk(k,j)=savedH[(j-begin)*m_nsp+k];
        }
    }
};
}
