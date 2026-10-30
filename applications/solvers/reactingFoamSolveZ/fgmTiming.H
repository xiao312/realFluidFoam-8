#ifndef fgmTiming_H
#define fgmTiming_H

#include "Pstream.H"
#include "scalarList.H"
#include "labelList.H"
#include <chrono>

// Local, inclusive counters. Only report() communicates, at caller-owned writes/end.
class fgmWallTiming
{
public:
    enum Category
    {
        startup, step, sourceFirstHalf, continuity, momentum, species,
        mixtureFraction, progress, sourceSecondHalf, reactionCorrection,
        energy, thermoCorrection, caloricAudit, pressure, transportCorrection,
        postPressureAudit, energyBudget, fieldWrite, categoryCount
    };
    using Clock = std::chrono::steady_clock;
    using Stamp = Clock::time_point;

private:
    const bool enabled_;
    const Stamp origin_;
    Foam::scalarList cumulative_, longest_;
    Foam::labelList calls_;

    static const char* name(const Foam::label category)
    {
        static const char* const names[] =
        {
            "startup", "step", "sourceFirstHalf", "continuity", "momentum",
            "species", "mixtureFraction", "progress", "sourceSecondHalf",
            "reactionCorrection", "energy", "thermoCorrection", "caloricAudit",
            "pressure", "transportCorrection", "postPressureAudit",
            "energyBudget", "fieldWrite"
        };
        return names[category];
    }

public:
    explicit fgmWallTiming(const bool enabled)
    :
        enabled_(enabled), origin_(enabled ? Clock::now() : Stamp()),
        cumulative_(categoryCount, 0), longest_(categoryCount, 0),
        calls_(categoryCount, 0)
    {}

    Stamp start() const { return enabled_ ? Clock::now() : Stamp(); }

    void stop(const Category category, const Stamp& begin)
    {
        if (!enabled_) return;
        const double seconds = std::chrono::duration<double>(Clock::now()-begin).count();
        cumulative_[category] += seconds;
        longest_[category] = Foam::max(longest_[category], Foam::scalar(seconds));
        ++calls_[category];
    }

    void report(const Foam::scalar time, const char* reason) const
    {
        if (!enabled_) return;
        using namespace Foam;
        // One rank-owned list; Pstream gathers it without per-region barriers.
        List<scalarList> ranks(Pstream::nProcs());
        scalarList& local = ranks[Pstream::myProcNo()];
        local.setSize(3*categoryCount + 1);
        local[3*categoryCount] = std::chrono::duration<double>(Clock::now()-origin_).count();
        for (label category = 0; category < categoryCount; ++category)
        {
            local[3*category] = cumulative_[category];
            local[3*category + 1] = longest_[category];
            local[3*category + 2] = calls_[category];
        }
        Pstream::gatherList(ranks);
        if (!Pstream::master()) return;

        Info<< "fgmTimingSummary t=" << time << " reason=" << reason
            << " ranks=" << ranks.size()
            << " clock=steady_wall inclusive=1 maximaAreOneCriticalPath=0 categories=(";
        for (label category = 0; category < categoryCount; ++category)
            Info<< (category ? " " : "") << name(category);
        Info<< ")" << nl;
        forAll(ranks, rank)
        {
            Info<< "fgmTimingRank t=" << time << " reason=" << reason
                << " rank=" << rank << " elapsed_s=" << ranks[rank][3*categoryCount];
            for (label column = 0; column < 3; ++column)
            {
                const char* labelText[] = {" cumulative_s=(", " maxCall_s=(", " calls=("};
                Info<< labelText[column];
                for (label category = 0; category < categoryCount; ++category)
                    Info<< (category ? " " : "") << ranks[rank][3*category+column];
                Info<< ")";
            }
            Info<< nl;
        }
        for (label category = 0; category < categoryCount; ++category)
        {
            label totalRank = 0, longestRank = 0;
            for (label rank = 1; rank < ranks.size(); ++rank)
            {
                if (ranks[rank][3*category] > ranks[totalRank][3*category]) totalRank = rank;
                if (ranks[rank][3*category+1] > ranks[longestRank][3*category+1]) longestRank = rank;
            }
            Info<< "fgmTimingCategory t=" << time << " reason=" << reason
                << " category=" << name(category)
                << " rank0Cumulative_s=" << ranks[0][3*category]
                << " maxCumulative_s=" << ranks[totalRank][3*category]
                << " maxCumulativeRank=" << totalRank
                << " maxCall_s=" << ranks[longestRank][3*category+1]
                << " maxCallRank=" << longestRank << nl;
        }
        Info<< endl;
    }
};
#endif
