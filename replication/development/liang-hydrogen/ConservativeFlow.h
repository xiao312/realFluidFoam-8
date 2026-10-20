#pragma once
#include "../cantera-liang/TotalEnthalpyFlow.h"
#include <filesystem>
#include <fstream>
#include <iomanip>

namespace hydrogen {
// Numerical control: species and total enthalpy share face mass flow, upwind
// states and dual-cell widths. All boundary and interior species rows remain.
class ConservativeFlow : public liang::TotalEnthalpyFlow {
public:
    explicit ConservativeFlow(std::shared_ptr<Cantera::Solution> solution)
        : liang::TotalEnthalpyFlow(solution,false) {}

    // Export native steady residuals and fluxes after solving. Boundary residuals
    // are excluded: connectors complete them outside Flow1D::evalSpecies.
    void writeBalances(const std::filesystem::path& output) {
        const auto nodesPath=output/"balance-nodes.csv",facesPath=output/"balance-faces.csv";
        if(std::filesystem::exists(nodesPath) || std::filesystem::exists(facesPath))
            throw std::runtime_error("Balance output already exists");
        std::vector<double> state(size()),residual(size(),0),enthalpy(m_points),partial(m_nsp);
        std::vector<int> diagonal(size(),0);
        for(size_t c=0;c<nComponents();c++) {
            const auto field=values(componentName(c));
            for(size_t j=0;j<m_points;j++)state[index(c,j)]=field[j];
        }
        updateProperties(Cantera::npos,state.data(),0,m_points-1);
        evalEnergy(state.data(),residual.data(),diagonal.data(),0,0,m_points-1);
        evalSpecies(state.data(),residual.data(),diagonal.data(),0,0,m_points-1);
        std::ofstream nodes(nodesPath),faces(facesPath);
        if(!nodes || !faces)throw std::runtime_error("Cannot write balance output");
        nodes<<std::setprecision(17)<<"x_m,T_K,rho_kg_m3,cp_J_kgK,massflow_kg_m2s,h_J_kg,interior,R_T_K_s";
        faces<<std::setprecision(17)<<"x_left_m,x_right_m,T_mid_K,massflow_kg_m2s,lambda_W_mK,H_adv_W_m2,H_cond_W_m2,H_species_W_m2,H_total_W_m2";
        for(const auto& name:m_thermo->speciesNames()) {
            nodes<<",Y_"<<name<<",source_"<<name<<",R_"<<name;
            faces<<",J_"<<name<<",G_"<<name<<",h_"<<name;
        }
        nodes<<'\n';faces<<'\n';
        for(size_t j=0;j<m_points;j++) {
            setGas(state.data(),j);enthalpy[j]=m_thermo->enthalpy_mass();
            const bool interior=j>0 && j+1<m_points;
            nodes<<z(j)<<','<<T(state.data(),j)<<','<<m_rho[j]<<','<<m_cp[j]<<','
                 <<rho_u(state.data(),j)<<','<<enthalpy[j]<<','<<interior<<','
                 <<(interior?residual[index(Cantera::c_offset_T,j)]:0.);
            for(size_t k=0;k<m_nsp;k++)
                nodes<<','<<Y(state.data(),k,j)<<','<<m_wt[k]*m_wdot(k,j)<<','
                     <<(interior?residual[index(Cantera::c_offset_Y+k,j)]:0.);
            nodes<<'\n';
        }
        for(size_t j=0;j+1<m_points;j++) {
            setGasAtMidpoint(state.data(),j);
            m_thermo->getPartialMolarEnthalpies(partial.data());
            const double mass=.5*(rho_u(state.data(),j)+rho_u(state.data(),j+1));
            const size_t upwind=mass>=0?j:j+1;
            const double advective=mass*enthalpy[upwind];
            const double conductive=-m_tcon[j]*(T(state.data(),j+1)-T(state.data(),j))/m_dz[j];
            double diffusion=0;
            for(size_t k=0;k<m_nsp;k++)diffusion+=m_flux(k,j)*partial[k]/m_wt[k];
            faces<<z(j)<<','<<z(j+1)<<','<<.5*(T(state.data(),j)+T(state.data(),j+1))
                 <<','<<mass<<','<<m_tcon[j]<<','<<advective<<','<<conductive<<','
                 <<diffusion<<','<<advective+conductive+diffusion;
            for(size_t k=0;k<m_nsp;k++)
                faces<<','<<m_flux(k,j)<<','<<mass*Y(state.data(),k,upwind)+m_flux(k,j)
                     <<','<<partial[k]/m_wt[k];
            faces<<'\n';
        }
        if(!nodes || !faces)throw std::runtime_error("Incomplete balance output");
    }
protected:
    void evalSpecies(double* x,double* residual,int* diagonal,double inverseTime,
                     size_t first,size_t last) override {
        if(!m_isFree || m_twoPointControl || m_do_radiation || m_do_soret)
            throw std::runtime_error("Conservative control requires adiabatic free flow without Soret");
        Cantera::Flow1D::evalSpecies(x,residual,diagonal,inverseTime,first,last);
        const size_t begin=std::max<size_t>(first,1);
        const size_t end=std::min(last,m_points-2);
        if(begin>end)return;
        const size_t base=begin-1;
        std::vector<double> faceMass(end-begin+2);
        for(size_t j=base;j<=end;j++)
            faceMass[j-base]=.5*(rho_u(x,j)+rho_u(x,j+1));
        for(size_t j=begin;j<=end;j++) {
            const double leftMass=faceMass[j-1-base],rightMass=faceMass[j-base];
            const size_t leftUpwind=leftMass>=0?j-1:j;
            const size_t rightUpwind=rightMass>=0?j:j+1;
            const double width=.5*(m_dz[j-1]+m_dz[j]);
            for(size_t k=0;k<m_nsp;k++) {
                const double leftFlux=leftMass*Y(x,k,leftUpwind)+m_flux(k,j-1);
                const double rightFlux=rightMass*Y(x,k,rightUpwind)+m_flux(k,j);
                residual[index(Cantera::c_offset_Y+k,j)]=
                    (m_wt[k]*m_wdot(k,j)-(rightFlux-leftFlux)/width)/m_rho[j]
                    -inverseTime*(Y(x,k,j)-Y_prev(k,j));
                diagonal[index(Cantera::c_offset_Y+k,j)]=1;
            }
        }
    }
};
}
