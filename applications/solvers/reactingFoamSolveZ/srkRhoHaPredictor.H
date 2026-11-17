#ifndef srkRhoHaPredictor_H
#define srkRhoHaPredictor_H
#include "srkRhoHaRecovery.H"
#include "fgmChemicalEnthalpy.H"
#include "fgmBoundaryEnthalpy.H"
#include "thermoInversionWitness.H"

// Returns the globally accepted predictor count. No density, internal Ha or
// history modification. Pressure must be solved again after a post-p predictor.
inline Foam::label applySrkRhoHaPredictor
(
    Foam::psiReactionThermo& thermo, const Foam::volScalarField& rho,
    Foam::volScalarField& Ha, const Foam::word& stage
)
{
    using namespace Foam;
    const Time& time=rho.mesh().time();
    if (!time.controlDict().lookupOrDefault<Switch>("realFluidRhoHaPredictor",false)) return 0;
    const PressureSlopeMixture* mixture=dynamic_cast<const PressureSlopeMixture*>(&thermo.composition());
    if (!mixture || thermo.he().name()!="h")
        FatalErrorInFunction<<"Density/Ha predictor requires the declared SRK sensible-enthalpy mixture"<<exit(FatalError);
    const scalar limit=time.controlDict().lookupOrDefault<scalar>("fgmThermoClosureRelativeLimit",1e-8);
    const scalarField heldDensity(rho.primitiveField()),heldHa(Ha.primitiveField());
    const tmp<volScalarField> literal=thermo.he(thermo.p(),thermo.T());
    const tmp<volScalarField> cp=thermo.Cp();
    label candidates=0,accepted=0,rejected=0;
    scalar maximumDeltaP=0,maximumDeltaT=0;
    forAll(thermo.he(),celli)
    {
        const scalar actual=literal()[celli],stored=thermo.he()[celli],T=thermo.T()[celli];
        const scalar scale=max(scalar(1),max(mag(actual),max(mag(stored),mag(cp()[celli]*T))));
        const scalar error=mag(actual-stored)/scale;
        if (std::isfinite(error+T+cp()[celli]) && T>0 && cp()[celli]>0 && error<=limit) continue;
        ++candidates;
        const auto result=recoverSrkDensityEnthalpy(mixture->cellMixture(celli),rho[celli],Ha[celli],thermo.p()[celli],T);
        if (!result.passed())
        {
            ++rejected;
            Pout<<"rhoHaPredictorRejected t="<<time.value()<<" stage="<<stage
                <<" rank="<<Pstream::myProcNo()<<" cell="<<celli
                <<" reason="<<result.reason<<" candidateT_K="<<result.temperature
                <<" candidateP_Pa="<<result.pressure<<" dPDRho="<<result.isothermalSlope
                <<" selectedDensityRelativeError="<<result.selectedDensityRelativeError<<endl;
            continue;
        }
        maximumDeltaP=max(maximumDeltaP,mag(result.pressure-thermo.p()[celli]));
        maximumDeltaT=max(maximumDeltaT,mag(result.temperature-T));
        thermo.p().primitiveFieldRef()[celli]=result.pressure;
        thermo.T().primitiveFieldRef()[celli]=result.temperature;
        ++accepted;
    }
    reduce(candidates,sumOp<label>());reduce(accepted,sumOp<label>());reduce(rejected,sumOp<label>());
    reduce(maximumDeltaP,maxOp<scalar>());reduce(maximumDeltaT,maxOp<scalar>());
    if (accepted)
    {
        thermo.p().correctBoundaryConditions();thermo.T().correctBoundaryConditions();
        updateFgmFixedTemperatureEnthalpy(thermo,thermo.composition(),Ha);
        thermo.he()==Ha-fgmChemicalEnthalpy(rho.mesh(),thermo.composition());
        writeThermoInversionWitness(thermo,rho,Ha,"beforePredictorRefresh");
        thermo.correct();
        const scalar densityMutation=gMax(mag(rho.primitiveField()-heldDensity));
        const scalar haMutation=gMax(mag(Ha.primitiveField()-heldHa));
        if (densityMutation!=0 || haMutation!=0)
            FatalErrorInFunction<<"Constraint predictor modified internal transported rho/Ha"<<exit(FatalError);
    }
    if (candidates)
        Info<<"rhoHaPredictor t="<<time.value()<<" stage="<<stage
            <<" candidates="<<candidates<<" accepted="<<accepted<<" rejected="<<rejected
            <<" maxDeltaP_Pa="<<maximumDeltaP<<" maxDeltaT_K="<<maximumDeltaT
            <<" internalRhoChanged=0 internalHaChanged=0 oldTimeChanged=0"
            <<" pressureEquationRequired="<<label(stage=="afterPressure" && accepted>0)<<endl;
    return accepted;
}
#endif
