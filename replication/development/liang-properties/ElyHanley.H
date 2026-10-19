// Ely–Hanley corresponding-states conductivity. See NOTICE for attribution.
#ifndef RF_ELY_HANLEY_H
#define RF_ELY_HANLEY_H
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>
namespace rfElyHanley {
constexpr double R=8314.46261815324, referenceW=16.04, referenceTc=190.4;
constexpr double referenceVc=.0986, referenceZc=.288, referenceOmega=.011;
struct Species { double Tc, Pc, Vc, W, omega, cp_R; };
enum class DensityMapping { molarVolume, massDensityShortcut };
inline void positive(double value, const char* name) {
    if (!(value>0) || !std::isfinite(value)) throw std::domain_error(name);
}
struct Shape { double f,h; };
inline Shape shape(double T,double V,const Species& s) {
    positive(T,"Ely-Hanley T");
    // Partial molar volumes can be negative, including trace/absent species.
    // The corresponding-states correlation bounds reduced volume to [0.5,2].
    if(!std::isfinite(V)) throw std::domain_error("Ely-Hanley partial molar volume");
    positive(s.Tc,"Ely-Hanley Tc"); positive(s.Pc,"Ely-Hanley Pc");
    positive(s.Vc,"Ely-Hanley Vc"); positive(s.W,"Ely-Hanley W");
    const double t=std::max(.5,std::min(2.,T/s.Tc));
    const double v=std::max(.5,std::min(2.,V/s.Vc));
    const double theta=1+(s.omega-referenceOmega)*(.090569-.862762*std::log(t)
        +(.316636-.465684/t)*(v-.5));
    const double z=s.Pc*s.Vc/(R*s.Tc);
    const double phi=(1+(s.omega-referenceOmega)*(.394901*(v-1.023545)
        -.932813*(v-.754639)*std::log(t)))*referenceZc/z;
    Shape out={s.Tc/referenceTc*theta,s.Vc/referenceVc*phi};
    positive(out.f,"Ely-Hanley f"); positive(out.h,"Ely-Hanley h"); return out;
}
inline double referenceViscosity(double T) {
    positive(T,"reference T"); T=std::min(T,10000.);
    const double c[]={2.907741307e6,-3.312874033e6,1.608101838e6,
        -4.331904871e5,7.062481330e4,-7.116620750e3,4.325174400e2,
        -1.445911210e1,.2037119479};
    double value=0; for(int i=0;i<9;++i) value+=c[i]*std::pow(T,(i-3.)/3.);
    return value*1e-7;
}
inline double referenceConductivity(double density_g_cm3,double T) {
    positive(T,"reference T");
    if(density_g_cm3<0 || !std::isfinite(density_g_cm3)) throw std::domain_error("reference density");
    const double r=density_g_cm3;
    const double dilute=15*R/(4*referenceW)*referenceViscosity(T);
    const double linear=(-.252762920+.334328590*std::pow(1.12-std::log(T/168.),2))*r;
    const double excess=std::exp(-7.197708227+85.678222640/T)*std::expm1(
        (12.471834689-984.62522975*std::pow(T,-1.5))*std::pow(r,.1)
        +(r/.1628-1)*std::sqrt(r)*(.35946850007+69.798412538/T-872.88332851/(T*T)));
    return dilute+1e-3*(linear+excess);
}
inline double conductivity(double T,double molarVolume,const std::vector<Species>& species,
    const std::vector<double>& X,const std::vector<double>& partialVolumes,
    DensityMapping mapping=DensityMapping::molarVolume) {
    positive(molarVolume,"mixture molar volume");
    const auto n=species.size();
    if(!n || X.size()!=n || partialVolumes.size()!=n) throw std::domain_error("Ely-Hanley input sizes");
    std::vector<Shape> shapes(n); std::vector<double> internal(n);
    double sumX=0,volumeSum=0,meanW=0;
    for(std::size_t i=0;i<n;++i) {
        if(X[i]<0 || !std::isfinite(X[i])) throw std::domain_error("mole fraction");
        sumX+=X[i]; volumeSum+=X[i]*partialVolumes[i];meanW+=X[i]*species[i].W;
        shapes[i]=shape(T,partialVolumes[i],species[i]); const auto s=shapes[i];
        const double mu=referenceViscosity(T/s.f)*std::sqrt(s.f*species[i].W/referenceW)*std::pow(s.h,-2./3.);
        // The author GRI atomic-N fit reaches Cp/R=2.49863767 near 2115 K.
        // Internal modes cannot contribute negative heat capacity. This bounded
        // transport-only correction does not alter thermo h/cp or kinetics.
        if(!std::isfinite(species[i].cp_R) || species[i].cp_R<2.5-.002) throw std::domain_error("ideal Cp/R below 2.5 beyond audited NASA-fit tolerance");
        internal[i]=mu/species[i].W*1.32*R*std::max(0.,species[i].cp_R-2.5);
    }
    if(std::abs(sumX-1)>1e-10 || std::abs(volumeSum/molarVolume-1)>1e-7)
        throw std::domain_error("mole fractions / partial molar Euler identity");
    double h=0,f=0,mass=0,lambdaInternal=0;
    for(std::size_t i=0;i<n;++i) for(std::size_t j=0;j<n;++j) {
        const double weight=X[i]*X[j];
        const double hij=std::pow(std::cbrt(shapes[i].h)+std::cbrt(shapes[j].h),3)/8;
        const double fij=std::sqrt(shapes[i].f*shapes[j].f);
        const double invW=.5*(species[i].W+species[j].W)/(species[i].W*species[j].W);
        h+=weight*hij; f+=weight*fij*hij;
        mass+=weight*std::sqrt(invW*fij)*std::pow(hij,-4./3.);
        const double sum=internal[i]+internal[j];
        if(sum>0) lambdaInternal+=weight*2*internal[i]*internal[j]/sum;
    }
    f/=h; const double W=std::pow(mass,-2)*f*std::pow(h,-8./3.);
    // h maps molar volume, so reference mass density must use methane W.
    // massDensityShortcut is a named diagnostic for the Cantera-3.2 formula,
    // not the molar-consistent default and not evidence of Liang's implementation.
    const double densityW=mapping==DensityMapping::molarVolume?referenceW:meanW;
    const double referenceDensity=densityW*h/molarVolume*1e-3;
    const double scale=std::sqrt(f*referenceW/W)*std::pow(h,-2./3.);
    const double value=lambdaInternal+scale*referenceConductivity(referenceDensity,T/f);
    positive(value,"Ely-Hanley conductivity"); return value;
}
}
#endif
