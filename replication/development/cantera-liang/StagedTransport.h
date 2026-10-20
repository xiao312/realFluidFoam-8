#pragma once
#include "SrkPhase.h"
#include "TakahashiTable.h"
#include "LightSpeciesSoret.h"
#include "../liang-properties/ElyHanley.H"
#include "cantera/transport/HighPressureGasTransport.h"
// Exported by the pinned Cantera 3.2 SDK, but not declared in its header.
namespace Cantera {double takahashiCorrectionFactor(double Pr,double Tr);}
namespace liang {
class StagedTransport : public Cantera::HighPressureGasTransport {
public:
    StagedTransport() = default;
    int stage=2;
    bool denseIncrementOnly=false;
    bool boundedTakahashi=false;
    bool smoothedAlpha=false;
    bool signedAlpha=false;
    bool table2=false;
    bool highTemperature=false;
    bool bulkTakahashi=false;
    bool manualSoret=false;
    size_t boundedPairCalls=0;
    std::vector<Species> parameters;
    size_t conductivityCalls=0,diffusionCalls=0;
    size_t negativePartialVolumeCalls=0;
    size_t projectedCompositionCalls=0;
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
    void getThermalDiffCoeffs(double* output) override {
        if(!manualSoret) {
            Cantera::MixTransport::getThermalDiffCoeffs(output);return;
        }
        std::vector<double> x(m_nsp),y(m_nsp),diffusion(m_nsp),theta(m_nsp,0.);
        m_thermo->getMoleFractions(x.data());
        // Transport-only projection follows the existing treatment of Newton
        // iterates. Final flame composition remains independently screened.
        double sum=0;
        for(auto& value:x) {value=std::max(0.,value);sum+=value;}
        if(!(sum>0))throw std::runtime_error("Empty Soret composition");
        const auto& weights=m_thermo->molecularWeights();
        double meanWeight=0;
        for(size_t k=0;k<m_nsp;k++) {x[k]/=sum;meanWeight+=x[k]*weights[k];}
        for(size_t k=0;k<m_nsp;k++)y[k]=x[k]*weights[k]/meanWeight;
        getMixDiffCoeffs(diffusion.data());
        for(size_t k=0;k<m_nsp;k++) {
            if(weights[k]>=5 || x[k]==0)continue;
            for(size_t j=0;j<m_nsp;j++) {
                if(j==k || x[j]==0)continue;
                // GasTransport's epsilon includes the same polar/nonpolar
                // effective-well-depth correction as the reviewed formula.
                const auto collision=manualCollisionRatios(k,j,m_thermo->temperature());
                theta[k]+=x[k]*x[j]*lightSpeciesPairFactor(collision,weights[k],weights[j]);
            }
        }
        const auto result=projectLightSpeciesSoret(m_thermo->density(),meanWeight,
                                                  weights,x,y,diffusion,theta);
        std::copy(result.begin(),result.end(),output);
    }
protected:
    // A derived transport may supply source-qualified pair ratios without
    // changing ordinary diffusion or the inherited Cantera Soret coefficient.
    virtual CollisionRatios manualCollisionRatios(size_t first,size_t second,double temperature) {
        return lightSpeciesCollisionRatios(
            std::log(Cantera::Boltzmann*temperature/m_epsilon(first,second)));
    }
public:
    void updateCorrectionFactors() override {
        if(!boundedTakahashi) {
            Cantera::HighPressureGasTransportBase::updateCorrectionFactors();return;
        }
        const double p=m_thermo->pressure();
        double bulkTc=0,bulkPc=0,bulkSum=0;
        if(bulkTakahashi) {
            for(size_t k=0;k<m_nsp;k++) {
                const double x=std::max(Cantera::Tiny,m_molefracs[k]);
                bulkTc+=x*m_Tcrit[k];bulkPc+=x*m_Pcrit[k];bulkSum+=x;
            }
            bulkTc/=bulkSum;bulkPc/=bulkSum;
        }
        for(size_t i=0;i<m_nsp;i++)for(size_t j=0;j<m_nsp;j++) {
            double xi=std::max(Cantera::Tiny,m_molefracs[i]);
            double xj=std::max(Cantera::Tiny,m_molefracs[j]);
            double sum=xi+xj;xi/=sum;xj/=sum;
            double tr=m_temp/(bulkTakahashi?bulkTc:xi*m_Tcrit[i]+xj*m_Tcrit[j]);
            double bounded=highTemperature?std::max(tr,1.):std::clamp(tr,1.,5.);
            if(bounded!=tr)boundedPairCalls++;
            double pr=p/(bulkTakahashi?bulkPc:xi*m_Pcrit[i]+xj*m_Pcrit[j]);
            double factor=Cantera::takahashiCorrectionFactor(pr,bounded);
            if(table2)factor+=takahashiTable2Delta(pr,bounded);
            if(!(factor>0 && std::isfinite(factor)))throw std::runtime_error("Invalid bounded Takahashi factor");
            m_P_corr_ij(i,j)=factor;
        }
    }
    double thermalConductivity() override {
        conductivityCalls++;
        if(stage<4)return Cantera::MixTransport::thermalConductivity();
        std::vector<double> x(m_nsp),v(m_nsp),cp(m_nsp);
        m_thermo->getMoleFractions(x.data());m_thermo->getPartialMolarVolumes(v.data());
        double molarVolume=1/m_thermo->molarDensity(),sum=0;bool projected=false;
        // FreeFlame Newton iterates admit small negative species fractions.
        // Like Cantera transport, evaluate transport on nonnegative fractions.
        // Recompute volume consistently for the projected transport-only state.
        for(auto& value:x) {if(value<0) {value=0;projected=true;}sum+=value;}
        if(projected || std::abs(sum-1)>1e-12) {
            if(!(sum>0))throw std::runtime_error("Invalid transport composition");
            for(auto& value:x)value/=sum;
            auto z=evaluate(m_thermo->temperature(),m_thermo->pressure(),x,parameters,smoothedAlpha,signedAlpha);
            v=z.vb;molarVolume=z.v;projectedCompositionCalls++;
        }
        if(*std::min_element(v.begin(),v.end())<0)negativePartialVolumeCalls++;
        m_thermo->getCp_R_ref(cp.data());
        std::vector<rfElyHanley::Species> s;
        for(size_t k=0;k<m_nsp;k++) {
            const auto& p=parameters[k];s.push_back({p.Tc,p.Pc,p.Vc,m_thermo->molecularWeight(k),p.omega,cp[k]});
        }
        double full=rfElyHanley::conductivity(m_thermo->temperature(),molarVolume,s,x,v);
        if(!denseIncrementOnly)return full;
        // Explicit diagnostic: retain the verified dilute transport baseline.
        double diluteVolume=R*m_thermo->temperature(); // ideal molar volume at 1 Pa
        std::vector<double> diluteVolumes(m_nsp,diluteVolume);
        double dilute=rfElyHanley::conductivity(m_thermo->temperature(),diluteVolume,s,x,diluteVolumes);
        double result=Cantera::MixTransport::thermalConductivity()+full-dilute;
        rfElyHanley::positive(result,"Dense-increment conductivity");return result;
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
