#ifndef relaxedTableClock_H
#define relaxedTableClock_H

#include "dictionary.H"
#include "error.H"
#include "scalar.H"
#include "word.H"
#include <cmath>

namespace Foam { namespace combustionModels {
struct RelaxationClock
{
    word mode;
    scalar alpha;
    scalar time;
};

// Numerical source-clock control only. No species repair or rate fitting.
inline RelaxationClock relaxedTableClock(const dictionary& coefficients, scalar dt)
{
    if (!std::isfinite(dt) || dt <= 0)
        FatalErrorInFunction << "relaxedTable requires positive finite deltaT" << exit(FatalError);
    const word mode = coefficients.lookupOrDefault<word>("relaxationMode", "steps");
    if (mode == "steps")
    {
        if (coefficients.found("relaxationTime"))
            FatalErrorInFunction << "Use relaxationTime only with relaxationMode fixedTime" << exit(FatalError);
        const scalar steps = coefficients.lookup<scalar>("relaxationSteps");
        if (!std::isfinite(steps) || steps < 1)
            FatalErrorInFunction << "relaxationSteps must be finite and at least1" << exit(FatalError);
        return {mode, 1/steps, steps*dt};
    }
    if (mode == "fixedTime" || mode == "fixedTimeExact")
    {
        if (coefficients.found("relaxationSteps"))
            FatalErrorInFunction << "Omit relaxationSteps when using relaxationMode fixedTime" << exit(FatalError);
        const scalar time = coefficients.lookup<scalar>("relaxationTime");
        if (mode == "fixedTimeExact")
        {
            if (!std::isfinite(time) || time <= 0)
                FatalErrorInFunction << "Exact relaxationTime must be positive and finite" << exit(FatalError);
            return {mode, -std::expm1(-dt/time), time};
        }
        if (!std::isfinite(time) || time <= 0 || dt > time)
            FatalErrorInFunction << "relaxationTime must be positive, finite and >= deltaT; set maxDeltaT accordingly" << exit(FatalError);
        return {mode, dt/time, time};
    }
    FatalErrorInFunction << "Unknown relaxationMode " << mode << "; use steps, fixedTime or fixedTimeExact" << exit(FatalError);
    return {mode, 0, 0};
}
}}
#endif
