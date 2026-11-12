#ifndef FORGE_FIXED_STATE_SOURCE_ODE_HPP
#define FORGE_FIXED_STATE_SOURCE_ODE_HPP

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>

namespace forgeFgm
{
struct SourceAdvance
{
    double progress;
    double elapsed;
    std::size_t crossedSegments;
    bool outwardBoundary;
};

// Fixed Z and rho only. Sources are kg/(m3 s); progress is a mass-fraction sum.
// A boundary event is evidence of missing coverage, never a clipped successful step.
class FixedStateSource
{
    std::vector<double> coordinates_;
    std::vector<double> sources_;

public:
    FixedStateSource(const std::vector<double>& coordinates,
                     const std::vector<double>& sources)
    : coordinates_(coordinates), sources_(sources)
    {
        if (coordinates.size() < 2 || sources.size() != coordinates.size())
            throw std::invalid_argument("Source curve requires matching coordinate/source arrays");
        for (std::size_t i = 0; i < coordinates.size(); ++i)
        {
            if (!std::isfinite(coordinates[i]) || !std::isfinite(sources[i]) ||
                (i && coordinates[i] <= coordinates[i-1]))
                throw std::invalid_argument("Source coordinates must increase strictly and all values must be finite");
        }
    }

    SourceAdvance advance(double density, double initial, double duration) const
    {
        if (!(density > 0) || !std::isfinite(density) || !std::isfinite(initial) ||
            !(duration >= 0) || !std::isfinite(duration))
            throw std::invalid_argument("Density, progress and duration are invalid");
        if (initial < coordinates_.front() || initial > coordinates_.back())
            throw std::out_of_range("Initial progress is outside table coverage");
        SourceAdvance result{initial, 0, 0, false};
        while (result.elapsed < duration)
        {
            auto high = std::upper_bound(coordinates_.begin(), coordinates_.end(), result.progress);
            std::size_t index = high == coordinates_.begin() ? 0 : std::size_t(high - coordinates_.begin() - 1);
            index = std::min(index, coordinates_.size() - 2);
            double slope = (sources_[index+1] - sources_[index]) /
                           (coordinates_[index+1] - coordinates_[index]) / density;
            double velocity = sources_[index] / density + slope * (result.progress - coordinates_[index]);
            // At the final knot, use its stored value instead of cancellation-prone reconstruction.
            if (result.progress == coordinates_.back()) velocity = sources_.back() / density;
            if (velocity == 0)
            {
                result.elapsed = duration;
                return result;
            }
            const bool positive = velocity > 0;
            if ((positive && result.progress == coordinates_.back()) ||
                (!positive && result.progress == coordinates_.front()))
            {
                result.outwardBoundary = true;
                return result;
            }
            if (!positive)
            {
                auto low = std::lower_bound(coordinates_.begin(), coordinates_.end(), result.progress);
                index = std::size_t(low - coordinates_.begin() - 1);
                slope = (sources_[index+1] - sources_[index]) /
                        (coordinates_[index+1] - coordinates_[index]) / density;
                // Velocity is continuous at a knot; retain its stored/interpolated value.
            }
            const double edge = positive ? coordinates_[index+1] : coordinates_[index];
            const double edgeVelocity = (positive ? sources_[index+1] : sources_[index]) / density;
            const double distance = edge - result.progress;
            // Intermediate ratios can exceed double range for a subnormal
            // velocity even when the physical update is finite. Keep traps on.
            const long double ratio = (long double)slope * distance / velocity;
            const bool rootBeforeEdge=edgeVelocity==0 ||
                std::signbit(edgeVelocity)!=std::signbit(velocity);
            const long double crossing = slope == 0 ? (long double)distance / velocity :
                (rootBeforeEdge ? std::numeric_limits<long double>::infinity() :
                 (std::abs(ratio) < .5L ? std::log1p(ratio) :
                  std::log(std::abs((long double)edgeVelocity))-
                  std::log(std::abs((long double)velocity))) / slope);
            const double remaining = duration - result.elapsed;
            if (crossing > remaining)
            {
                const long double delta = slope == 0 ? (long double)velocity * remaining :
                    (long double)velocity * std::expm1((long double)slope * remaining) / slope;
                const long double next=(long double)result.progress+delta;
                if (!std::isfinite(next) || next<coordinates_.front() || next>coordinates_.back())
                    throw std::runtime_error("Analytic source update left coverage");
                result.progress = (double)next;
                if (result.progress < coordinates_.front() || result.progress > coordinates_.back())
                    throw std::runtime_error("Analytic source advance left coverage before its computed event");
                result.elapsed = duration;
                return result;
            }
            if (crossing < 0 || !std::isfinite(crossing))
                throw std::runtime_error("Invalid analytic source segment crossing");
            result.progress = edge; // Exact knot event, not overshoot clipping.
            result.elapsed += (double)crossing;
            if (++result.crossedSegments > 2 * coordinates_.size())
                throw std::runtime_error("Unexpected source direction cycle");
        }
        return result;
    }
};
}
#endif
