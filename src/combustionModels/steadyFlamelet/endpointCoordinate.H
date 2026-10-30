#ifndef steadyEndpointCoordinate_H
#define steadyEndpointCoordinate_H
#include <cmath>
#include <limits>
#include <sstream>
#include <iomanip>
#include <stdexcept>

namespace forgeSteady
{
struct EndpointCoordinate { double raw, value, delta; };
inline double endpointRoundoffLimit()
{
    return 64*std::numeric_limits<double>::epsilon();
}
inline EndpointCoordinate endpointCoordinate(double raw, bool allowRoundoff)
{
    const double delta = raw < 0 ? raw : raw > 1 ? raw-1 : 0;
    if (!std::isfinite(raw) || (delta != 0 &&
        (!allowRoundoff || std::abs(delta) > endpointRoundoffLimit())))
    {
        std::ostringstream message;
        message << std::setprecision(17)
            << "endpoint-coordinate rawZ=" << raw << " outsideDelta=" << delta
            << " limit=" << endpointRoundoffLimit()
            << " policy=" << (allowRoundoff ? "endpoint64epsilon" : "strict")
            << "; transported Z is unchanged; lookup refused";
        throw std::runtime_error(message.str());
    }
    return {raw, delta == 0 ? raw : raw < 0 ? 0.0 : 1.0, delta};
}
}
#endif
