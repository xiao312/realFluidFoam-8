#ifndef RF_TRACKING_CORE_H
#define RF_TRACKING_CORE_H
#include <vector>
#include <deque>
#include <cmath>
#include <string>
#include <stdexcept>
#include <algorithm>
namespace flameTracking
{
struct Point { double x, T, OH, rho, U; };
struct Sample
{
    std::string status="missing_contour";
    int crossings=0;
    double x=NAN, rho=NAN, U=NAN, freshRho=NAN, freshU=NAN, freshT=NAN;
};
inline Sample sample(const std::vector<Point>& p, bool temperature, double level,
                     bool left, double freshTemperature)
{
    if(p.size()<20) throw std::runtime_error("Need 20 cells for fresh region");
    Sample s;
    const auto count=p.size()/20;
    double rho=0,U=0,T=0;
    for(std::size_t i=0;i<count;++i)
    {const auto& q=p[left?i:p.size()-1-i];rho+=q.rho;U+=q.U;T+=q.T;}
    s.freshRho=rho/count;s.freshU=U/count;s.freshT=T/count;
    const double middle=(p.front().x+p.back().x)/2;
    std::size_t index=0;
    for(std::size_t i=0;i+1<p.size();++i)
    {
        const auto& a=p[i];const auto& b=p[i+1];
        if(!(b.x>a.x)) throw std::runtime_error("Nonmonotone mesh coordinates");
        const double ya=temperature?a.T:a.OH, yb=temperature?b.T:b.OH;
        const bool crossed=left?(b.x<=middle && ya<=level && yb>level)
                               :(a.x>=middle && ya>level && yb<=level);
        if(crossed){++s.crossings;index=i;}
    }
    if(s.crossings!=1)
    {if(s.crossings>1)s.status="ambiguous_contour";return s;}
    if(!(s.freshRho>0) || std::abs(s.freshT-freshTemperature)>2)
    {s.status="invalid_fresh_region";return s;}
    const auto& a=p[index];const auto& b=p[index+1];
    const double ya=temperature?a.T:a.OH,yb=temperature?b.T:b.OH;
    const double f=(level-ya)/(yb-ya);
    s.x=a.x+f*(b.x-a.x);s.rho=a.rho+f*(b.rho-a.rho);s.U=a.U+f*(b.U-a.U);
    s.status=std::isfinite(s.x)&&std::isfinite(s.U)&&s.rho>0?"valid":"invalid_fields";
    return s;
}
struct Entry { double t; Sample s; };
struct Result
{
    std::string status="warmup";
    int count=0;
    double start=NAN,end=NAN, laboratory=NAN,freshRelative=NAN,weighted=NAN;
    double secant=NAN,fitResidual=NAN;
};
class History
{
    std::deque<Entry> entries_;
public:
    Result add(double t,const Sample& s,bool left,double window)
    {
        Result out;
        if(s.status!="valid"){entries_.clear();out.status=s.status;return out;}
        if(!entries_.empty() && t<=entries_.back().t)
            throw std::runtime_error("Nonincreasing tracking time");
        const double sign=left?-1:1;
        if(!entries_.empty())
        {
            const auto& old=entries_.back();
            const double v=(s.x-old.s.x)/(t-old.t);
            out.secant=sign*.5*(s.rho/s.freshRho*(v-s.U)+old.s.rho/old.s.freshRho*(v-old.s.U));
        }
        entries_.push_back({t,s});
        // Retain the bracketing sample so the window covers at least its duration.
        while(entries_.size()>2 && entries_[1].t<=t-window) entries_.pop_front();
        out.count=entries_.size();out.start=entries_.front().t;out.end=t;
        if(out.count<3 || t-out.start<window*(1-1e-8))return out;
        double meanT=0,meanX=0;
        for(const auto& e:entries_){meanT+=e.t-t;meanX+=e.s.x;}
        meanT/=out.count;meanX/=out.count;
        double numerator=0,denominator=0;
        for(const auto& e:entries_)
        {double dt=e.t-t-meanT;numerator+=dt*(e.s.x-meanX);denominator+=dt*dt;}
        if(!(denominator>0))throw std::runtime_error("Degenerate tracking fit");
        const double velocity=numerator/denominator;
        double weighted=0,fresh=0,residual=0;
        for(const auto& e:entries_)
        {
            weighted+=e.s.rho/e.s.freshRho*(velocity-e.s.U);
            fresh+=velocity-e.s.freshU;
            residual=std::max(residual,std::abs(e.s.x-meanX-velocity*(e.t-t-meanT)));
        }
        out.laboratory=sign*velocity;out.weighted=sign*weighted/out.count;
        out.freshRelative=sign*fresh/out.count;out.fitResidual=residual;out.status="valid";
        return out;
    }
};
}
#endif
