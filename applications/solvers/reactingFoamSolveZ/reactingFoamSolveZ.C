/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Copyright (C) 2011-2020 OpenFOAM Foundation
     \\/     M anipulation  |
-------------------------------------------------------------------------------
License
    This file is part of OpenFOAM.

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

Application
    reactingFoam

Description
    Variant of reactingFoam in which the mixture fraction Z is TRANSPORTED.

    The base solver reads Z from the case and never assigns it, so a table
    lookup sits at one prescribed mixture fraction.  This variant is a separate
    executable selected by name: it solves a transport equation for the model's
    own Z field (CombustionModel::mixtureFraction()) and then lets the table read
    that solved field.  Nothing in this file changes the model, the table, the
    chemistry or the base reactingFoam executable; the difference between the two
    solvers is the single #include of ZEqn.H below and this comment.

\*---------------------------------------------------------------------------*/

#include "fvCFD.H"
#include "fluidThermoMomentumTransportModel.H"
#include "psiReactionThermophysicalTransportModel.H"
#include "psiReactionThermo.H"
#include "CombustionModel.H"
#include "multivariateScheme.H"
#include "pimpleControl.H"
#include "pressureControl.H"
#include "fvOptions.H"
#include "localEulerDdtScheme.H"
#include "fvcSmooth.H"
#include "fgmChemicalEnthalpy.H"
#include "fgmBoundaryEnthalpy.H"
#include "fgmMatrixResidual.H"
#include "fgmThermoClosure.H"
#include "srkPressureDensitySlope.H"
#include "srkColdEnergyProjection.H"
#include "srkRhoHaPredictor.H"
#include "fgmTable.H"
#include "fgmTiming.H"
#include <sstream>
#include <iomanip>
#include "fgmContinuityStage.H"
#include "zRoundoffDecision.H"
#include "relaxationProbe.H"
#include "pressureDampingFactor.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

int main(int argc, char *argv[])
{
    argList::addBoolOption("relaxation-probe", "One-cell species relaxation/Ha source diagnostic;zero CFD steps");
    #include "postProcess.H"

    #include "setRootCaseLists.H"
    #include "createTime.H"
    #include "createMesh.H"
    #include "createControl.H"
    #include "createTimeControls.H"
    #include "initContinuityErrs.H"
    #include "createFields.H"
    #include "createFieldRefs.H"

    if (args.optionFound("relaxation-probe"))
    {
        if (!absoluteEnthalpyFGM)
            FatalErrorInFunction << "Relaxation probe requires absolute Ha" << exit(FatalError);
        return auditRelaxedSpeciesSource(thermo,reaction(),mesh,runTime,fgmAbsoluteEnthalpy());
    }

    #include "createFgmIgnition.H"

    if (runTime.controlDict().lookupOrDefault<Switch>("realFluidColdEnergyProjection",false)
        && reaction->lookupOrDefault<word>("combustionModel","")!="none")
        FatalErrorInFunction << "Cold projection supports nonreacting diagnostics only"
            << exit(FatalError);
    turbulence->validate();

    #include "energyState.H"
    #include "lowMachPressureAudit.H"
    fgmTiming.stop(fgmWallTiming::startup, fgmStartupStart);

    if (!LTS)
    {
        #include "compressibleCourantNo.H"
        #include "setInitialDeltaT.H"
    }

    // * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

    const bool realFluidInnerThermoCorrectors = runTime.controlDict()
        .lookupOrDefault<Switch>("realFluidInnerThermoCorrectors", false);
    const bool coupledRhoHaState=runTime.controlDict().lookupOrDefault<Switch>
        ("realFluidRhoHaPredictor",false);
    const bool deferCaloricTrialAudit=runTime.controlDict().lookupOrDefault<Switch>
        ("realFluidDeferCaloricTrialAudit",false);
    if (deferCaloricTrialAudit && (!absoluteEnthalpyFGM || !realFluidInnerThermoCorrectors
        || pimple.nCorrPiso()<2
        || !runTime.controlDict().lookupOrDefault<Switch>("realFluidPressureThermoRefresh",false)
        || !runTime.controlDict().lookupOrDefault<Switch>("writeFgmThermoClosure",false)))
        FatalErrorInFunction<<"Deferred caloric trials require absolute Ha, inner corrections, refresh/audit and nCorrectors>=2; final audit remains mandatory"<<exit(FatalError);
    const label maxRhoHaPressureIterations=coupledRhoHaState
        ? runTime.controlDict().lookupOrDefault<label>("maxRhoHaPressureIterations",6) : 1;
    if (coupledRhoHaState && (!absoluteEnthalpyFGM || !conserveTransportDensity
        || !realFluidInnerThermoCorrectors || pimple.nCorrPiso()<2
        || !runTime.controlDict().lookupOrDefault<Switch>("realFluidPressureThermoRefresh",false)
        || !runTime.controlDict().lookupOrDefault<Switch>("writeFgmThermoClosure",false)
        || maxRhoHaPressureIterations<1 || maxRhoHaPressureIterations>50))
        FatalErrorInFunction<<"Rho/Ha predictor requires absoluteHa, conservative rho, inner thermo, refresh/audit, nCorrectors>=2 and 1..50 pressure/property iterations"<<exit(FatalError);
    // Factory aliases (e.g. none) need not equal the C++ runtime type.
    const word selectedCombustionModel = reaction->lookupOrDefault<word>("combustionModel", "");
    if (realFluidInnerThermoCorrectors && selectedCombustionModel!="none"
        && selectedCombustionModel!="steadyFlamelet" && selectedCombustionModel!="relaxedTable"
        && !(selectedCombustionModel=="fgmTable" && splitFgmSource))
        FatalErrorInFunction << "Inner scalar/energy lifecycle requires none, steadyFlamelet, relaxedTable or strangFixedState fgmTable; got "
            << selectedCombustionModel << " (runtime type " << reaction->type() << "). "
            << "Other finite-rate/progress-source lifecycles are unsupported" << exit(FatalError);
    if (realFluidInnerThermoCorrectors && splitFgmSource)
        Info<< "fgmSourcePicard firstHalf=oncePerPhysicalStep transportAnchor=unchangedOldTime"
            << " secondHalf=recomputedFromTransport priorIterateNotAdvanced=1"
            << " physicalQualification=pending" << endl;
    Info<< "scalarEnergyCorrectors=" << (realFluidInnerThermoCorrectors ? "insidePressure" : "outerPimple") << endl;

    Info<< "\nStarting time loop\n" << endl;

    while (pimple.run(runTime))
    {
        const auto fgmStepStart = fgmTiming.start();
        #include "readTimeControls.H"

        // readTimeControls restores the dictionary value each step. Apply the
        // optional event-specific cap again before selecting the next deltaT.
        if (!fgmColdFlowActive && fgmPostIgnitionMaxDeltaT > 0)
            maxDeltaT = min(maxDeltaT, fgmPostIgnitionMaxDeltaT);

        if (LTS)
        {
            #include "setRDeltaT.H"
        }
        else
        {
            #include "compressibleCourantNo.H"
            #include "setDeltaT.H"
        }

        #include "densityPredictorTimeStep.H"
        #include "scheduledFgmIgnition.H"

        runTime++;

        #include "beginFgmSourceStep.H"

        Info<< "Time = " << runTime.timeName() << nl << endl;

        const auto fgmContinuityStart = fgmTiming.start();
        #include "rhoEqn.H"
        fgmTiming.stop(fgmWallTiming::continuity, fgmContinuityStart);

        while (pimple.loop())
        {
            // c and energy use sources sampled at the same lookup state.
            tmp<volScalarField> tabulatedHeatRelease;
            const auto fgmMomentumStart = fgmTiming.start();
            #include "UEqn.H"
            fgmTiming.stop(fgmWallTiming::momentum, fgmMomentumStart);
            if (!realFluidInnerThermoCorrectors)
            {
                #include "solveScalarsAndEnergy.H"
            }

            // --- Pressure corrector loop
            while (pimple.correct())
            {
                if (realFluidInnerThermoCorrectors)
                {
                    #include "solveScalarsAndEnergy.H"
                }
                const auto fgmPressureStart = fgmTiming.start();
                #include "pressureThermoCorrector.H"
                if (absoluteEnthalpyFGM)
                {
                    updateFgmFixedTemperatureEnthalpy(thermo, composition, fgmAbsoluteEnthalpy());
                }
                fgmTiming.stop(fgmWallTiming::pressure, fgmPressureStart);
            }

            if (pimple.turbCorr())
            {
                const auto fgmTransportStart = fgmTiming.start();
                turbulence->correct();
                thermophysicalTransport->correct();
                fgmTiming.stop(fgmWallTiming::transportCorrection, fgmTransportStart);
            }
        }

        if (deferCaloricTrialAudit)
        {
            auditFgmThermoClosure(thermo);
            if (runTime.timeIndex()==1 || runTime.writeTime())
                Info<<"thermoCoupledFinalAudit t="<<runTime.value()
                    <<" originalCaloricCriterionPassed=1 scientificAcceptance=0"<<endl;
        }
        auditFgmContinuityStage("beforeFinalEOSDensity", rho, phi);
        const bool preserveRefreshedTransportDensity=conserveTransportDensity
            && runTime.controlDict().lookupOrDefault<Switch>("realFluidPressureThermoRefresh",false);
        if (preserveRefreshedTransportDensity)
        {
            auditFgmContinuityStage("afterFinalTransportDensityPreservation",rho,phi);
        }
        else
        {
            rho=thermo.rho();
            auditFgmContinuityStage("afterFinalEOSDensity",rho,phi);
        }

        // A changed nonideal pressure can move h(p,T,Y) after the last inversion.
        // Measure that coupling drift separately; do not mutate or reject it as
        // an inversion error while it awaits another PIMPLE correction.
        const auto fgmPostPressureStart = fgmTiming.start();
        auditFgmThermoClosure(thermo, false);
        fgmTiming.stop(fgmWallTiming::postPressureAudit, fgmPostPressureStart);
        const auto fgmBudgetStart = fgmTiming.start();
        #include "energyState.H"
        #include "lowMachPressureAudit.H"
        fgmTiming.stop(fgmWallTiming::energyBudget, fgmBudgetStart);

        const auto fgmWriteStart = fgmTiming.start();
        runTime.write();
        fgmTiming.stop(fgmWallTiming::fieldWrite, fgmWriteStart);
        fgmTiming.stop(fgmWallTiming::step, fgmStepStart);
        if (runTime.writeTime()) fgmTiming.report(runTime.value(), "write");

        Info<< "ExecutionTime = " << runTime.elapsedCpuTime() << " s"
            << "  ClockTime = " << runTime.elapsedClockTime() << " s"
            << nl << endl;
    }

    fgmTiming.report(runTime.value(), "end");
    Info<< "End\n" << endl;

    return 0;
}


// ************************************************************************* //
