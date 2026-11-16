#ifndef FORGE_FGM_MAPPED_SOURCE_H
#define FORGE_FGM_MAPPED_SOURCE_H
#include "fgmSourceOde.H"

namespace forgeFgm
{
inline std::size_t& mappedSourceFallbackCount()
{
    static std::size_t count=0;
    return count;
}
// Raw-C knots can coincide after rounding even though the original eta knots
// are distinct (e.g. a subnormal Z next to a pure-stream zero-span row).
// Integrate the same piecewise-linear function in eta only in that case.
// No coordinate tolerance, chemistry adjustment or boundary policy is added.
inline SourceAdvance advanceMappedSource
(
    const std::vector<double>& raw,
    const std::vector<double>& eta,
    const std::vector<double>& sources,
    const double density, const double initial, const double duration
)
{
    if (raw.size()<2 || eta.size()!=raw.size() || sources.size()!=raw.size())
        throw std::invalid_argument("Mapped source arrays differ");
    bool collapsed=false;
    for (std::size_t j=0;j<raw.size();++j)
    {
        if (!std::isfinite(raw[j]) || (j && raw[j]<raw[j-1]))
            throw std::invalid_argument("Invalid mapped source coordinates");
        if (j && raw[j]==raw[j-1]) collapsed=true;
    }
    if (!collapsed) return FixedStateSource(raw,sources).advance(density,initial,duration);
    const long double lower=raw.front(), span=(long double)raw.back()-lower;
    if (!(span>0) || eta.front()!=0 || eta.back()!=1 || !std::isfinite(initial)
        || initial<raw.front() || initial>raw.back())
        throw std::invalid_argument("Invalid nonzero mapped source span/state");
    ++mappedSourceFallbackCount();
    std::vector<double> rates(sources.size());
    for (std::size_t j=0;j<sources.size();++j)
    {
        const long double rate=(long double)sources[j]/span;
        if (!std::isfinite(rate) || std::abs(rate)>std::numeric_limits<double>::max())
            throw std::overflow_error("Normalized mapped source rate is not representable");
        rates[j]=static_cast<double>(rate);
    }
    const double start=static_cast<double>(((long double)initial-lower)/span);
    SourceAdvance result=FixedStateSource(eta,rates).advance(density,start,duration);
    result.progress=static_cast<double>(lower+span*result.progress);
    return result;
}
}
#endif
