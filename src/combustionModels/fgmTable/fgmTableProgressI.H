// Included once by fgmTableReader.C. Version-2 progress mapping is isolated
// here so that the legacy text parser and interpolation remain recognizable.
void Foam::fgm::fgmTableReader::validateProgressMapping() const
{
    if (!mappedMassFraction())
    {
        if (schema_ != "forge-fgm-table-v1" || progressMin_.size()
            || progressMax_.size() || progressSpecies_.size())
        {
            refuse("v2 requires mass-fraction-mapped; mapping headers are not valid in v1");
        }
        return;
    }
    if (schema_ != "forge-fgm-table-v2") refuse("mass-fraction-mapped requires v2 schema");
    if (progressMin_.size() != nZ_ || progressMax_.size() != nZ_)
        refuse("v2 needs c-min and c-max with one finite value per Z row");
    if (progressSpecies_.empty()) refuse("v2 needs progress-species defining the raw mass-fraction sum");
    if (mag(c_[0]) > 1e-12 || mag(c_[nC_ - 1] - 1) > 1e-12)
        refuse("v2 c axis is lookup eta and must span 0 to 1");

    List<label> indices(progressSpecies_.size(), -1);
    forAll(progressSpecies_, k)
    {
        for (label previous = 0; previous < k; ++previous)
            if (progressSpecies_[previous] == progressSpecies_[k])
                refuse("duplicate progress species " + progressSpecies_[k]);
        forAll(species_, s)
            if (species_[s] == progressSpecies_[k]) indices[k] = s;
        if (indices[k] < 0) refuse("unknown progress species " + progressSpecies_[k]);
    }
    for (label i = 0; i < nZ_; ++i)
    {
        const scalar lo = progressMin_[i];
        const scalar hi = progressMax_[i];
        if (!std::isfinite(lo) || !std::isfinite(hi) || lo > hi || lo < -1e-12 || hi > 1 + 1e-12)
            refuse("invalid raw progress interval at Z row " + std::to_string(i));
        for (label j = 0; j < nC_; ++j)
        {
            scalar sum = 0;
            forAll(indices, k) sum += Y_[indices[k]][i*nC_ + j];
            const scalar expected = lo + c_[j]*(hi - lo);
            if (mag(sum - expected) > 1e-8)
                refuse("raw progress differs from species sum at node "
                    + std::to_string(i) + "," + std::to_string(j));
            if (hi == lo)
            {
                // A collapsed coordinate cannot represent multiple states.
                forAll(Y_, s)
                    if (mag(Y_[s][i*nC_ + j] - Y_[s][i*nC_]) > 1e-12)
                        refuse("zero-span progress row has varying composition");
                if (mag(Sc_[i*nC_ + j] - Sc_[i*nC_]) > 1e-10*max(scalar(1), mag(Sc_[i*nC_])))
                    refuse("zero-span progress row has varying source");
                if (mag(Q_[i*nC_ + j] - Q_[i*nC_]) > 1e-10*max(scalar(1), mag(Q_[i*nC_])))
                    refuse("zero-span progress row has varying heat release");
                if (hasTdiag() && mag(Tdiag_[i*nC_ + j] - Tdiag_[i*nC_]) > 1e-8)
                    refuse("zero-span progress row has varying temperature");
            }
        }
    }
}

Foam::scalar Foam::fgm::fgmTableReader::mappedProgress
(
    const label i,
    const scalar wZ,
    const scalar C
) const
{
    if (!std::isfinite(C)) refuse("raw progress C is non-finite");
    const scalar lo = (1 - wZ)*progressMin_[i] + wZ*progressMin_[i + 1];
    const scalar hi = (1 - wZ)*progressMax_[i] + wZ*progressMax_[i + 1];
    scalar bounded = C;
    if (C < lo || C > hi)
    {
        if (policy_ != CLAMP_TO_BOUNDS)
            refuse("raw C=" + numStr(C) + " outside local progress interval ["
                + numStr(lo) + "," + numStr(hi) + "]");
        bounded = min(max(C, lo), hi);
        ++clipCount_;
        maxProgressExcursion_ = max(maxProgressExcursion_, mag(C - bounded));
    }
    if (hi == lo) return 0;
    return (bounded - lo)/(hi - lo);
}
