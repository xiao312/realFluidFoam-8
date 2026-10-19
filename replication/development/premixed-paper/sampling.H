// SPDX-License-Identifier: GPL-3.0-or-later
#ifndef RF_PAPER_SAMPLING_H
#define RF_PAPER_SAMPLING_H
#include <vector>
#include <algorithm>
#include <cmath>
#include <string>
#include <stdexcept>
namespace paperFlame
{
struct Point { double x, Y, gradient, rho, U, T, p, source, diffusion; };
struct Sample
{
    std::string status = "missing_contour";
    int crossings = 0;
    double x=NAN, rho=NAN, U=NAN, gradient=NAN;
    double freshRho=NAN, freshT=NAN, freshP=NAN, freshU=NAN;
    double chemical=NAN, diffusive=NAN, speed=NAN;
};
inline Sample sample(const std::vector<Point>& points, double level, bool left)
{
    if (points.size()<20) throw std::runtime_error("Need at least 20 x cells");
    Sample out;
    const std::size_t coldCount=points.size()/20;
    double rho=0, T=0, p=0, U=0, maxOH=0;
    for (std::size_t k=0; k<coldCount; ++k)
    {
        const Point& q=points[left ? k : points.size()-1-k];
        rho+=q.rho; T+=q.T; p+=q.p; U+=q.U; maxOH=std::max(maxOH,q.Y);
    }
    out.freshRho=rho/coldCount; out.freshT=T/coldCount;
    out.freshP=p/coldCount; out.freshU=U/coldCount;
    const double middle=(points.front().x+points.back().x)/2;
    std::size_t crossing=0;
    for (std::size_t k=0; k+1<points.size(); ++k)
    {
        const Point& a=points[k]; const Point& b=points[k+1];
        if (!(b.x>a.x)) throw std::runtime_error("Nonunique/nonmonotone x cells");
        const bool valid=left ? (b.x<=middle && a.Y<=level && b.Y>level)
                              : (a.x>=middle && a.Y>level && b.Y<=level);
        if (valid) { ++out.crossings; crossing=k; }
    }
    if (out.crossings!=1)
    {
        if (out.crossings>1) out.status="ambiguous_contour";
        return out;
    }
    if (!(out.freshRho>0) || maxOH>level*0.1)
    { out.status="invalid_fresh_region"; return out; }
    const Point& a=points[crossing]; const Point& b=points[crossing+1];
    const double fraction=(level-a.Y)/(b.Y-a.Y);
    const auto interp=[&](double u,double v) {return u+fraction*(v-u);};
    out.x=interp(a.x,b.x); out.rho=interp(a.rho,b.rho);
    out.U=interp(a.U,b.U); out.gradient=interp(a.gradient,b.gradient);
    if (!std::isfinite(out.gradient) || std::abs(out.gradient)<1e-12
        || (left ? out.gradient<=0 : out.gradient>=0))
    { out.status="invalid_gradient"; return out; }
    const double denominator=out.freshRho*std::abs(out.gradient);
    out.chemical=interp(a.source,b.source)/denominator;
    out.diffusive=interp(a.diffusion,b.diffusion)/denominator;
    out.speed=out.chemical+out.diffusive;
    out.status=std::isfinite(out.speed) ? "valid" : "nonfinite_terms";
    return out;
}
}
#endif
