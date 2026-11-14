// Intentional multi-include statement block; caller supplies a local scope.
// Keep source/transport/enthalpy ordering identical in both coupling modes.
            const auto fgmSpeciesStart = fgmTiming.start();
            #include "YEqn.H"
            fgmTiming.stop(fgmWallTiming::species, fgmSpeciesStart);
            const auto fgmMixtureStart = fgmTiming.start();
            if (reaction->compositionTabulated())
            {
                #include "ZEqn.H"
            }
            fgmTiming.stop(fgmWallTiming::mixtureFraction, fgmMixtureStart);
            if (reaction->transportsProgress())
            {
                const auto fgmProgressStart = fgmTiming.start();
                #include "cEqn.H"
                fgmTiming.stop(fgmWallTiming::progress, fgmProgressStart);
            }
            else if (reaction->compositionTabulated())
            {
                // A steady flamelet owns Y(Z), not a transported progress field.
                // Refresh the just-transported composition before Ha inversion.
                const auto fgmReactionStart = fgmTiming.start();
                reaction->correct();
                fgmTiming.stop(fgmWallTiming::reactionCorrection, fgmReactionStart);
            }
            const auto fgmEnergyStart = fgmTiming.start();
            #include "EEqn.H"
            fgmTiming.stop(fgmWallTiming::energy, fgmEnergyStart);

