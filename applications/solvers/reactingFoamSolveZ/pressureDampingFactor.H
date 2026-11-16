#ifndef pressureDampingFactor_H
#define pressureDampingFactor_H
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>

namespace Foam
{
// Same global factor must be applied to p and phi, never directly to density.
// For Euler continuity rho(alpha) is affine in phi. Retaining10% of the
// positive reference density gives this bound; repeated nonlinear solves
// may still reach the original undamped solution. No physical floor is added.
template<class Values>
inline double pressureDensityDampingFactor(const Values& reference, const Values& candidate)
{
    if (reference.size() != candidate.size())
        throw std::invalid_argument("Pressure damping density sizes differ");
    double factor=1;
    for (std::size_t i=0; i<static_cast<std::size_t>(reference.size()); ++i)
    {
        const double base=reference[i], trial=candidate[i];
        if (!std::isfinite(base) || base<=0 || !std::isfinite(trial))
            throw std::invalid_argument("Invalid pressure damping reference/trial cell "+std::to_string(i));
        if (trial<base) factor=std::min(factor,0.9*base/(base-trial));
    }
    if (!std::isfinite(factor) || factor<=0 || factor>1)
        throw std::invalid_argument("No positive pressure damping step");
    return factor;
}
}
#endif
