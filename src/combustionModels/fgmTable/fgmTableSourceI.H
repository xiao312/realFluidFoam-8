// Included once by fgmTableReader.C; source integration is stricter than lookup.
void Foam::fgm::fgmTableReader::sourceCurve
(
    const scalar Z,
    std::vector<double>& coordinates,
    std::vector<double>& sources
) const
{
    if (!mappedMassFraction())
        throw std::invalid_argument("Source integration requires a v2 raw-C table");
    if (!std::isfinite(Z) || Z < z_[0] || Z > z_[nZ_-1])
        throw std::out_of_range("Source stage Z is outside table coverage");
    label i = 0;
    scalar weight = 0;
    cell(z_, Z, "source Z", i, weight);
    const scalar lower = (1-weight)*progressMin_[i] + weight*progressMin_[i+1];
    const scalar upper = (1-weight)*progressMax_[i] + weight*progressMax_[i+1];
    coordinates.resize(nC_);
    sources.resize(nC_);
    for (label j = 0; j < nC_; ++j)
    {
        coordinates[j] = j == 0 ? lower : (j == nC_-1 ? upper : lower + c_[j]*(upper-lower));
        sources[j] = (1-weight)*Sc_[i*nC_+j] + weight*Sc_[(i+1)*nC_+j];
    }
}

forgeFgm::SourceAdvance Foam::fgm::fgmTableReader::advanceSource
(
    const scalar Z, const scalar density,
    const scalar initial, const scalar duration
) const
{
    if (!(density > 0) || !std::isfinite(density) || !std::isfinite(initial)
     || !(duration >= 0) || !std::isfinite(duration))
        throw std::invalid_argument("Invalid fixed-state source inputs");
    std::vector<double> coordinates, sources;
    sourceCurve(Z, coordinates, sources);
    if (coordinates.front() == coordinates.back())
    {
        if (initial != coordinates.front())
            throw std::out_of_range("Source stage C differs from its zero-span row");
        if (duration == 0) return {initial, 0, 0, false};
        for (const double source : sources)
            if (source != 0) return {initial, 0, 0, true};
        return {initial, duration, 0, false};
    }
    return forgeFgm::FixedStateSource(coordinates, sources).advance(density, initial, duration);
}
