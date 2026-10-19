#include "sampling.H"
#include <cassert>
#include <iostream>
int main()
{
    std::vector<paperFlame::Point> points;
    for (int i=0;i<100;++i)
    {
        double x=(i+0.5)*1e-5;
        double Y=std::max(0.,std::min((x-0.0002)*2.,(0.0008-x)*2.));
        points.push_back({x,Y,x<0.0005?2.:-2.,10.,0.,298.,10132500.,2.,-.8});
    }
    for (bool left : {true,false})
    {
        auto s=paperFlame::sample(points,2e-5,left);
        assert(s.status=="valid" && s.crossings==1);
        assert(std::abs(s.speed-.06)<1e-12);
        assert(std::abs(s.chemical-.1)<1e-12);
        assert(std::abs(s.diffusive+.04)<1e-12);
        assert(std::abs(s.x-(left?.00021:.00079))<1e-12);
        assert(paperFlame::sample(points,1.,left).status=="missing_contour");
    }
    for (auto& p:points) p.source=-2.;
    assert(paperFlame::sample(points,2e-5,false).speed<0);
    std::cout << "PASS: mirrored fronts, interpolation, diffusion sign, missing level, signed speed\n";
}
