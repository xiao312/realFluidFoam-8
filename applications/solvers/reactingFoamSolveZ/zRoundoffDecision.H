#ifndef zRoundoffDecision_H
#define zRoundoffDecision_H

#include <cmath>
#include <limits>
#include <stdexcept>

namespace forgeZRoundoff
{
inline double limit() { return 64*std::numeric_limits<double>::epsilon(); }

// The caller must scan globally before applying any result. This routine never
// mutates input; the fixed bound is not a user-controlled physics tolerance.
inline void requireRange(double minimum, double maximum, unsigned long invalid)
{
    if (invalid || !std::isfinite(minimum) || !std::isfinite(maximum)
     || minimum > maximum || minimum < -limit() || maximum > 1+limit())
        throw std::runtime_error("Z roundoff projection refused: invalid state or excursion exceeds fixed64epsilon");
}

inline double projected(double value)
{
    requireRange(value,value,0);
    return value < 0 ? 0 : value > 1 ? 1 : value;
}
}
#endif
