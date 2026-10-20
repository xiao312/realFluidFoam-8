#pragma once
#include "StagedTransport.h"
#include "cantera/oneD/Flow1D.h"
#include <fstream>
#include <iomanip>
#include <limits>

namespace liang {
class SoretOutput {
public:
    virtual ~SoretOutput() = default;
    virtual void writeSoretFluxes(const std::string& path) = 0;
};
// Cantera 3.2 checks model names, rather than the mixture-transport interface.
// Its pinned _finalize uses m_do_soret only in that check, then initializes
// temperatures and the fixed point. Native property/flux/energy paths are kept.
template<class Base>
class SoretCompatibleFlow : public Base, public SoretOutput {
public:
    using Base::Base;

    void _finalize(const double* x) override {
        if (!this->m_do_soret ||
            this->m_trans->transportModel() == "mixture-averaged" ||
            this->m_trans->transportModel() == "mixture-averaged-CK") {
            Base::_finalize(x);
            return;
        }
        if (this->m_do_multicomponent ||
            this->m_trans->transportModel() != "liang-staged" ||
            !dynamic_cast<StagedTransport*>(this->m_trans)) {
            throw std::runtime_error("Unqualified Soret transport compatibility");
        }
        struct RestoreFlag {
            bool& flag;
            ~RestoreFlag() { flag = true; }
        } restore{this->m_do_soret};
        this->m_do_soret = false;
        Base::_finalize(x);
    }

    void writeSoretFluxes(const std::string& path) override {
        if(!this->m_do_soret)throw std::runtime_error("Soret output requested while disabled");
        std::vector<double> state(this->nComponents()*this->m_points);
        for(size_t c=0;c<this->nComponents();c++) {
            const auto values=this->values(this->componentName(c));
            for(size_t j=0;j<this->m_points;j++)state[this->index(c,j)]=values[j];
        }
        this->updateProperties(Cantera::npos,state.data(),0,this->m_points-1);
        std::ofstream out(path);
        if(!out)throw std::runtime_error("Cannot write Soret profile");
        out<<std::setprecision(std::numeric_limits<double>::max_digits10)
           <<"x_left_m,x_right_m,T_mid_K,species,DT_kg_m_s,ordinary_kg_m2_s,soret_kg_m2_s,total_kg_m2_s,partial_h_J_kg\n";
        std::vector<double> enthalpy(this->m_nsp);
        for(size_t j=0;j<this->m_points-1;j++) {
            this->setGasAtMidpoint(state.data(),j);
            this->m_thermo->getPartialMolarEnthalpies(enthalpy.data());
            double left=this->T(state.data(),j),right=this->T(state.data(),j+1);
            double gradient=2*(right-left)/((right+left)*this->m_dz[j]);
            for(size_t k=0;k<this->m_nsp;k++) {
                double thermal=-this->m_dthermal(k,j)*gradient;
                out<<this->z(j)<<','<<this->z(j+1)<<','<<.5*(left+right)<<','
                   <<this->m_thermo->speciesName(k)<<','<<this->m_dthermal(k,j)<<','
                   <<this->m_flux(k,j)-thermal<<','<<thermal<<','<<this->m_flux(k,j)<<','
                   <<enthalpy[k]/this->m_wt[k]<<'\n';
            }
        }
        if(!out)throw std::runtime_error("Incomplete Soret profile write");
    }
};
}
