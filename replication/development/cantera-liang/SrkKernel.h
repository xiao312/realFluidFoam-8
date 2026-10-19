// Molar SI units: kmol, m3, K, Pa, J. No Cantera dependency.
#pragma once
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>
namespace liang {
constexpr double R=8314.46261815324;
struct Species { double Tc,Pc,Vc,W,omega; bool eos=true; };
struct State {
    double T,p,v,b,a,at,att,pv,pt,h,cp,s;
    std::vector<double> hb,vb,lnphi;
};
inline State evaluate(double T,double p,const std::vector<double>& x,
                      const std::vector<Species>& species) {
    if (!(T>0 && p>0) || x.size()!=species.size()) throw std::domain_error("SRK state");
    const size_t n=x.size();
    std::vector<double> si(n),sti(n),bi(n);
    double q=0,qt=0,b=0;
    for(size_t i=0;i<n;i++) {
        const auto& z=species[i];
        if(!z.eos) continue;
        double m=.48+1.574*z.omega-.176*z.omega*z.omega;
        double c=std::sqrt(.42747*(R*z.Tc)*(R*z.Tc)/z.Pc);
        double bracket=1+m*(1-std::sqrt(T/z.Tc));
        double sign=bracket<0?-1:1;
        si[i]=c*std::abs(bracket);
        sti[i]=-sign*c*m/(2*std::sqrt(T*z.Tc));
        bi[i]=.08664*R*z.Tc/z.Pc;
        q+=x[i]*si[i]; qt+=x[i]*sti[i]; b+=x[i]*bi[i];
    }
    State z{}; z.T=T;z.p=p;z.b=b;z.a=q*q;z.at=2*q*qt;
    z.att=2*qt*qt-q*qt/T;z.hb.resize(n);z.vb.resize(n);z.lnphi.resize(n);
    if(b<1e-30) {z.v=R*T/p;z.pv=-p/z.v;z.pt=p/T;
        std::fill(z.vb.begin(),z.vb.end(),z.v);return z;}
    const double A=z.a*p/std::pow(R*T,2),B=b*p/(R*T);
    // Z^3 - Z^2 + (A-B-B^2) Z - A B = 0; select largest real gas root.
    const double c=A-B-B*B, d=-A*B;
    const double pp=c-1./3,qq=-2./27+c/3+d,disc=qq*qq/4+pp*pp*pp/27;
    double Z;
    if(disc>=0) Z=1./3+std::cbrt(-qq/2+std::sqrt(disc))+std::cbrt(-qq/2-std::sqrt(disc));
    else Z=1./3+2*std::sqrt(-pp/3)*std::cos(std::acos(std::clamp(
        -qq/(2*std::sqrt(-pp*pp*pp/27)),-1.,1.))/3);
    z.v=Z*R*T/p;const double v=z.v,a=z.a,at=z.at;
    if(!(v>b)) throw std::domain_error("SRK gas root below covolume");
    z.pv=-R*T/std::pow(v-b,2)+a*(2*v+b)/std::pow(v*(v+b),2);
    z.pt=R/(v-b)-at/(v*(v+b));
    if(!(z.pv<0)) throw std::domain_error("SRK unstable gas root");
    const double vt=-z.pt/z.pv,L=std::log1p(b/v),C=T*at-a;
    z.h=p*v-R*T+C*L/b;
    z.cp=p*vt-R+T*z.att*L/b-C*vt/(v*(v+b));
    z.s=R*std::log(p*(v-b)/(R*T))+at*L/b;
    std::vector<double> hx(n),vx(n);double hxmean=0,vxmean=0;
    for(size_t i=0;i<n;i++) {
        double ax=2*q*si[i],atx=2*(qt*si[i]+q*sti[i]);
        double px=R*T*bi[i]/std::pow(v-b,2)-ax/(v*(v+b))+a*bi[i]/(v*std::pow(v+b,2));
        vx[i]=-px/z.pv;
        double lx=bi[i]/(v+b)-b*vx[i]/(v*(v+b));
        hx[i]=p*vx[i]+(T*atx-ax)*L/b+C*(lx/b-L*bi[i]/(b*b));
        hxmean+=x[i]*hx[i];vxmean+=x[i]*vx[i];
        z.lnphi[i]=bi[i]/b*(Z-1)-std::log(Z-B)
            -(q>0 ? A/B*(2*si[i]/q-bi[i]/b)*L:0);
    }
    for(size_t i=0;i<n;i++) {z.hb[i]=z.h+hx[i]-hxmean;z.vb[i]=v+vx[i]-vxmean;}
    return z;
}
}
