// Call the qualified OpenFOAM EOS; no thermodynamic inversion or T clipping.
#include "soaveRedlichKwong.H"
#include "rfSpecie.H"
#include "IFstream.H"
#include "scalarList.H"
#include "ElyHanley.H"
#include <fstream>
#include <iomanip>
#include <array>
using namespace Foam;
using EOS=soaveRedlichKwong<rfSpecie>;
constexpr double gasR=8314.46261815324;
struct Coefficients { double b,c1,c2,c3; };
Coefficients mix(const std::vector<EOS>& eos,const std::vector<double>& x) {
    double b=0,A=0,C=0;
    for(std::size_t i=0;i<eos.size();++i) {
        b+=x[i]*eos[i].bM();
        A+=x[i]*std::sqrt(eos[i].coef1());
        C+=x[i]*eos[i].coef2()/(2*std::sqrt(eos[i].coef1()));
    }
    return {b,A*A,2*A*C,C*C};
}
void critical(std::ostream& out,const char* fuel,double phi,const Coefficients& c) {
    const double q=1+std::cbrt(2.)+std::cbrt(4.);
    const double ratio=q*q*(q+1)*(q+1)/((q-1)*(q-1)*(2*q+1));
    // Solve c1 - c2 sqrt(T) + (c3 - ratio R b) T = 0 on physical branch.
    const double A=std::sqrt(c.c1),C=c.c2/(2*A);
    const double T=std::pow(A/(C+std::sqrt(ratio*gasR*c.b)),2);
    const double v=q*c.b,a=c.c1-c.c2*std::sqrt(T)+c.c3*T;
    const double p=gasR*T/(v-c.b)-a/(v*(v+c.b));
    const double d1=-gasR*T/std::pow(v-c.b,2)+a*(2*v+c.b)/(v*v*std::pow(v+c.b,2));
    const double d2=2*gasR*T/std::pow(v-c.b,3)
        -2*a*(3*v*v+3*c.b*v+c.b*c.b)/(v*v*v*std::pow(v+c.b,3));
    out<<fuel<<','<<phi<<','<<T<<','<<p/101325<<','<<v<<','<<d1*v/p<<','<<d2*v*v/p<<'\n';
}
int main(int argc,char**argv) {
    if(argc!=3) {std::cerr<<"Usage: rfLiangPropertyProbe DICTIONARY OUTPUT_DIR\n";return 2;}
    try {
        IFstream input(argv[1]); dictionary data(input);
        const std::string root=argv[2];
        EOS oxygen(data.subDict("O2"));
        const dictionary& caloric=data.subDict("O2").subDict("thermodynamics");
        const scalarList low(caloric.lookup("lowCpCoeffs")),high(caloric.lookup("highCpCoeffs"));
        const double common=readScalar(caloric.lookup("Tcommon"));
        const double lower=readScalar(caloric.lookup("Tlow"));
        std::ofstream o(root+"/oxygen.csv");
        o<<std::setprecision(16)<<"T_K,p_Pa,rho_kg_m3,kappa_W_m_K,cp0_R,caloric_extrapolated\n";
        for(int k=0;k<=900;++k) {
            const double T=100+k,p=10132500,rho=oxygen.rho(p,T),v=oxygen.W()/rho;
            const scalarList& coeff=T<common?low:high;
            double cp=0;for(int j=4;j>=0;--j)cp=cp*T+coeff[j];
            rfElyHanley::Species s={oxygen.Tc(),oxygen.Pc(),oxygen.Vc()*1e-3,oxygen.W(),oxygen.omega(),cp};
            const double lambda=rfElyHanley::conductivity(T,v,{s},{1},{v});
            o<<T<<','<<p<<','<<rho<<','<<lambda<<','<<cp<<','<<(T<lower)<<'\n';
        }
        std::ofstream c(root+"/critical.csv");
        c<<std::setprecision(16)<<"fuel,phi,Tc_K,Pc_atm,vc_m3_kmol,dp_normalized,d2p_normalized\n";
        for(const char* fuel:{"H2","CH4"}) {
            const double oxygenPerFuel=std::string(fuel)=="H2"?.5:2.;
            std::vector<EOS> eos={EOS(data.subDict(fuel)),oxygen,EOS(data.subDict("N2"))};
            for(int j=0;j<=140;++j) {
                const double phi=.6+.01*j,den=phi+oxygenPerFuel/0.21;
                std::vector<double> x={phi/den,oxygenPerFuel/den,oxygenPerFuel*79/21/den};
                critical(c,fuel,phi,mix(eos,x));
            }
        }
        std::ofstream pure(root+"/pure-critical.csv");
        pure<<std::setprecision(16)<<"fuel,phi,Tc_K,Pc_atm,vc_m3_kmol,dp_normalized,d2p_normalized\n";
        for(const char* name:{"H2","O2","N2","CH4"}) {
            EOS e(data.subDict(name));critical(pure,name,1,mix({e},{1}));
        }
        o.close();c.close();pure.close();
        if(!o || !c || !pure)throw std::runtime_error("Cannot write property outputs");
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
    return 0;
}
