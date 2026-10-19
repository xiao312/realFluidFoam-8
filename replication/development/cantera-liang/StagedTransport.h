#pragma once
#include "SrkPhase.h"
#include "../liang-properties/ElyHanley.H"
#include "cantera/transport/HighPressureGasTransport.h"
namespace liang {
class StagedTransport : public Cantera::HighPressureGasTransport {
public:
    StagedTransport() = default;
    int stage=2;
    std::vector<Species> parameters;
    size_t conductivityCalls=0,diffusionCalls=0;
    size_t negativePartialVolumeCalls=0;
    std::string transportModel() const override {return "liang-staged";}
    void init(Cantera::ThermoPhase* gas,int mode=0) override {
        Cantera::MixTransport::init(gas,mode);
        if(parameters.size()!=m_nsp) throw std::runtime_error("Transport parameter count");
        m_Tcrit.resize(m_nsp);m_Pcrit.resize(m_nsp);m_Vcrit.resize(m_nsp);m_Zcrit.resize(m_nsp);
        for(size_t k=0;k<m_nsp;k++) {
            const auto& p=parameters[k];m_Tcrit[k]=p.Tc;m_Pcrit[k]=p.Pc;m_Vcrit[k]=p.Vc;
            m_Zcrit[k]=p.Pc*p.Vc/(R*p.Tc);
        }
        m_P_corr_ij.resize(m_nsp,m_nsp);
    }
    double viscosity() override {return Cantera::GasTransport::viscosity();}
    double thermalConductivity() override {
        conductivityCalls++;
        if(stage<4)return Cantera::MixTransport::thermalConductivity();
        std::vector<double> x(m_nsp),v(m_nsp),cp(m_nsp);
        m_thermo->getMoleFractions(x.data());m_thermo->getPartialMolarVolumes(v.data());
        if(*std::min_element(v.begin(),v.end())<0)negativePartialVolumeCalls++;
        m_thermo->getCp_R_ref(cp.data());
        std::vector<rfElyHanley::Species> s;
        for(size_t k=0;k<m_nsp;k++) {
            const auto& p=parameters[k];s.push_back({p.Tc,p.Pc,p.Vc,m_thermo->molecularWeight(k),p.omega,cp[k]});
        }
        return rfElyHanley::conductivity(m_thermo->temperature(),1/m_thermo->molarDensity(),s,x,v);
    }
    void getMixDiffCoeffs(double* d) override {
        diffusionCalls++;
        if(stage<5)Cantera::GasTransport::getMixDiffCoeffs(d);
        else Cantera::HighPressureGasTransportBase::getMixDiffCoeffs(d);
    }
    void getMixDiffCoeffsMass(double* d) override {
        diffusionCalls++;
        if(stage<5)Cantera::GasTransport::getMixDiffCoeffsMass(d);
        else Cantera::HighPressureGasTransportBase::getMixDiffCoeffsMass(d);
    }
    void getMixDiffCoeffsMole(double* d) override {
        diffusionCalls++;
        if(stage<5)Cantera::GasTransport::getMixDiffCoeffsMole(d);
        else Cantera::HighPressureGasTransportBase::getMixDiffCoeffsMole(d);
    }
    void getBinaryDiffCoeffs(size_t ld,double* d) override {
        if(stage<5)Cantera::GasTransport::getBinaryDiffCoeffs(ld,d);
        else Cantera::HighPressureGasTransportBase::getBinaryDiffCoeffs(ld,d);
    }
};
}
