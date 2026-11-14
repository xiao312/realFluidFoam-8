// Constant-p0, open-domain low-Mach model; default coupled path is unchanged.
const Switch lowMachPressureSplit=runTime.controlDict().lookupOrDefault<Switch>
    ("realFluidLowMachPressureSplit",false);
scalar lowMachBackgroundPressure=0;
autoPtr<volScalarField> mechanicalPressure;
label lowMachReferenceCell=0;
scalar lowMachReferenceValue=0;
if (lowMachPressureSplit)
{
    lowMachBackgroundPressure=readScalar
        (runTime.controlDict().lookup("realFluidThermodynamicPressure"));
    if (!(lowMachBackgroundPressure>0) || LTS || pimple.transonic()
     || thermo.he().name()!="h"
     || runTime.controlDict().lookupOrDefault<Switch>("realFluidDifferentialPressure",false)
     || runTime.controlDict().lookupOrDefault<Switch>("realFluidDensityTimeCorrection",false))
        FatalErrorInFunction << "Constant-p0 low-Mach model requires positive p0, h, "
            << "global nontransonic time and no compressible density-time option"
            << exit(FatalError);
    const scalar mismatch=gMax(mag(thermo.p().primitiveField()
        -lowMachBackgroundPressure))/lowMachBackgroundPressure;
    if (mismatch>1e-12)
        FatalErrorInFunction << "Initial EOS p must equal prescribed p0; mismatch="
            << mismatch << exit(FatalError);
    mechanicalPressure.reset(new volScalarField
    (
        IOobject("pMechanical",runTime.timeName(),mesh,
            IOobject::NO_READ,IOobject::AUTO_WRITE),
        thermo.p()
    ));
    lowMachReferenceValue=lowMachBackgroundPressure;
    setRefCell(mechanicalPressure(),pimple.dict(),
        lowMachReferenceCell,lowMachReferenceValue);
    Info<< "pressureModel=constantThermodynamicBackgroundLowMach p0_Pa="
        << lowMachBackgroundPressure
        << " momentumPressure=pMechanical energy=thermalEnthalpy"
        << " acoustics=absent physicalQualification=pending" << endl;
}
volScalarField& p=lowMachPressureSplit ? mechanicalPressure() : thermo.p();
