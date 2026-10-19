#pragma once
#include "SrkKernel.h"
#include "cantera/thermo/IdealGasPhase.h"
namespace liang {
class SrkPhase : public Cantera::IdealGasPhase {
public:
    int stage=2;
    bool fugacityKinetics=false;
    std::vector<Species> parameters;
    mutable size_t eosCalls=0,enthalpyCalls=0,cpCalls=0,partialCalls=0;
    std::string type() const override {return "liang-srk";}
    bool isIdeal() const override {return false;}
    const State& state() const {
        std::vector<double> x(nSpecies());getMoleFractions(x.data());
        if(cachedT!=temperature() || cachedRho!=density() || x!=cachedX) {
            auto c=evaluate(temperature(),1e5,x,parameters);
            double v=1/molarDensity();
            double p=R*temperature()/(v-c.b)-c.a/(v*(v+c.b));
            cached=evaluate(temperature(),p,x,parameters);
            cachedT=temperature();cachedRho=density();cachedX=x;
        }
        return cached;
    }
    double pressure() const override {
        if(parameters.empty()) return IdealGasPhase::pressure();
        return state().p;
    }
    void setPressure(double p) override {
        if(parameters.empty()) {IdealGasPhase::setPressure(p);return;}
        std::vector<double> x(nSpecies());getMoleFractions(x.data());
        cached=evaluate(temperature(),p,x,parameters);eosCalls++;
        setDensity(meanMolecularWeight()/cached.v);
        cachedT=temperature();cachedRho=density();cachedX=x;
    }
    double enthalpy_mole() const override {
        enthalpyCalls++;return IdealGasPhase::enthalpy_mole()+(stage>=3?state().h:0);
    }
    double cp_mole() const override {
        cpCalls++;return IdealGasPhase::cp_mole()+(stage>=3?state().cp:0);
    }
    double entropy_mole() const override {
        return IdealGasPhase::entropy_mole()+(stage>=3?state().s:0);
    }
    double intEnergy_mole() const override {return enthalpy_mole()-pressure()/molarDensity();}
    double gibbs_mole() const override {return enthalpy_mole()-temperature()*entropy_mole();}
    double cv_mole() const override {
        const auto& z=state();return cp_mole()+temperature()*z.pt*z.pt/z.pv;
    }
    double isothermalCompressibility() const override {return -1/(state().v*state().pv);}
    double thermalExpansionCoeff() const override {return -state().pt/(state().v*state().pv);}
    double soundSpeed() const override {
        return std::sqrt(cp_mole()/cv_mole()/isothermalCompressibility()/density());
    }
    void setState_DP(double,double) override {throw std::runtime_error("SRK DP setter unsupported; use TPX/TPY");}
    void getPartialMolarEnthalpies(double* h) const override {
        partialCalls++;IdealGasPhase::getPartialMolarEnthalpies(h);
        if(stage>=3) for(size_t k=0;k<nSpecies();k++) h[k]+=state().hb[k];
    }
    void getPartialMolarVolumes(double* v) const override {
        if(parameters.empty()) {IdealGasPhase::getPartialMolarVolumes(v);return;}
        std::copy(state().vb.begin(),state().vb.end(),v);
    }
    void getPartialMolarIntEnergies(double* u) const override {
        getPartialMolarEnthalpies(u);
        for(size_t k=0;k<nSpecies();k++) u[k]-=pressure()*state().vb[k];
    }
    void getActivityCoefficients(double* a) const override {
        if(parameters.empty()) {IdealGasPhase::getActivityCoefficients(a);return;}
        if(stage<3) throw std::runtime_error("Case 2 is an EOS-only ablation; equilibrium unsupported");
        for(size_t k=0;k<nSpecies();k++) a[k]=std::exp(state().lnphi[k]);
    }
    void getChemPotentials(double* mu) const override {
        if(parameters.empty()) {IdealGasPhase::getChemPotentials(mu);return;}
        if(stage<3) throw std::runtime_error("Case 2 equilibrium unsupported");
        IdealGasPhase::getChemPotentials(mu);
        for(size_t k=0;k<nSpecies();k++) mu[k]+=RT()*state().lnphi[k];
    }
    void getPartialMolarEntropies(double* s) const override {
        std::vector<double> mu(nSpecies());getChemPotentials(mu.data());getPartialMolarEnthalpies(s);
        for(size_t k=0;k<nSpecies();k++) s[k]=(s[k]-mu[k])/temperature();
    }
    void getPartialMolarCp(double* cp) const override {
        IdealGasPhase::getPartialMolarCp(cp);
        if(stage<3)return;
        std::vector<double> x(nSpecies());getMoleFractions(x.data());
        double dt=temperature()*1e-5;
        auto hi=evaluate(temperature()+dt,pressure(),x,parameters);
        auto lo=evaluate(temperature()-dt,pressure(),x,parameters);
        for(size_t k=0;k<nSpecies();k++) cp[k]+=(hi.hb[k]-lo.hb[k])/(2*dt);
    }
    void getActivityConcentrations(double* c) const override {
        if(!fugacityKinetics) {getConcentrations(c);return;}
        for(size_t k=0;k<nSpecies();k++) c[k]=moleFraction(k)*pressure()/RT()*std::exp(state().lnphi[k]);
    }
    void getActivities(double* a) const override {
        getActivityCoefficients(a);
        for(size_t k=0;k<nSpecies();k++)a[k]*=moleFraction(k);
    }
    void getdlnActCoeffdlnN(const size_t ld,double* const values) override {
        getdlnActCoeffdlnN_numderiv(ld,values);
    }
    void setToEquilState(const double*) override {
        throw std::runtime_error("Use VCS equilibrium for SRK; ideal element-potential setter is disabled");
    }
private:
    mutable double cachedT=-1,cachedRho=-1;
    mutable std::vector<double> cachedX;
    mutable State cached{};
};
}
