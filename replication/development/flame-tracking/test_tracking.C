#include "trackingCore.H"
#include <cassert>
#include <iostream>
int main()
{
    for(bool left:{true,false})
    {
        flameTracking::History h;const double sign=left?-1:1;
        flameTracking::Result r;
        for(int i=0;i<=10;++i)
        {
            flameTracking::Sample s;s.status="valid";s.x=.002+sign*.4*i*1e-6;
            s.rho=20;s.freshRho=100;s.U=sign*.1;s.freshU=sign*.34;
            r=h.add(i*1e-6,s,left,5e-6);
            if(i<5)assert(r.status=="warmup");
        }
        assert(r.status=="valid");assert(std::abs(r.weighted-.06)<1e-10);
        assert(std::abs(r.freshRelative-.06)<1e-10);assert(std::abs(r.laboratory-.4)<1e-10);
        assert(std::abs(r.secant-.06)<1e-10);assert(r.fitResidual<1e-12);
        flameTracking::Sample bad;bad.status="ambiguous_contour";
        assert(h.add(11e-6,bad,left,5e-6).status=="ambiguous_contour");
    }
    std::vector<flameTracking::Point> p;
    for(int i=0;i<100;++i)
    {double x=(i+.5)*.004/100;double f=std::max(0.,1-std::abs(x-.002)/.0005);p.push_back({x,298+1500*f,.001*f,100-80*f,0});}
    for(bool left:{true,false})
    {
        auto s=flameTracking::sample(p,true,798,left,298);
        assert(s.status=="valid");assert(std::abs(s.x-(.002+(left?-1:1)*.0005*2/3))<1e-12);
    }
    for(auto& q:p)if(q.x<.001)q.T=800;
    assert(flameTracking::sample(p,true,1000,true,298).status=="invalid_fresh_region");
    std::cout<<"PASS: manufactured tracking signs, weighting, windows and sampling\n";
}
