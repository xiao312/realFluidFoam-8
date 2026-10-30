// OF8 postProcess.H also includes this file before the normal solve path.
// Keep the timer in the same scope as every field-initialization call.
fgmWallTiming fgmTiming
(
    runTime.controlDict().lookupOrDefault<Switch>("writeFgmTiming", false)
);
const auto fgmStartupStart = fgmTiming.start();

#include "createRDeltaT.H"

Info<< "Reading thermophysical properties\n" << endl;
autoPtr<psiReactionThermo> pThermo(psiReactionThermo::New(mesh));
psiReactionThermo& thermo = pThermo();
thermo.validate(args.executable(), "h", "e");

basicSpecieMixture& composition = thermo.composition();
PtrList<volScalarField>& Y = composition.Y();

const word inertSpecie(thermo.lookup("inertSpecie"));
if (!composition.species().found(inertSpecie))
{
    FatalIOErrorIn(args.executable().c_str(), thermo)
        << "Inert specie " << inertSpecie << " not found in available species "
        << composition.species() << exit(FatalIOError);
}

volScalarField rho
(
    IOobject
    (
        "rho",
        runTime.timeName(),
        mesh
    ),
    thermo.rho()
);

Info<< "Reading field U\n" << endl;
volVectorField U
(
    IOobject
    (
        "U",
        runTime.timeName(),
        mesh,
        IOobject::MUST_READ,
        IOobject::AUTO_WRITE
    ),
    mesh
);

volScalarField& p = thermo.p();

#include "compressibleCreatePhi.H"

pressureControl pressureControl(p, rho, pimple.dict(), false);

mesh.setFluxRequired(p.name());

Info << "Creating turbulence model.\n" << nl;
autoPtr<compressible::momentumTransportModel> turbulence
(
    compressible::momentumTransportModel::New
    (
        rho,
        U,
        phi,
        thermo
    )
);

Info<< "Creating thermophysical transport model\n" << endl;
autoPtr<psiReactionThermophysicalTransportModel> thermophysicalTransport
(
    psiReactionThermophysicalTransportModel::New(turbulence(), thermo)
);

Info<< "Creating reaction model\n" << endl;
autoPtr<CombustionModel<psiReactionThermo>> reaction
(
    CombustionModel<psiReactionThermo>::New(thermo, turbulence())
);

const Switch conserveTabulatedDensity
(
    runTime.controlDict().lookupOrDefault<Switch>("conserveTabulatedDensity", false)
);
if (conserveTabulatedDensity && !reaction->compositionTabulated())
{
    FatalErrorInFunction
        << "conserveTabulatedDensity requires a tabulated composition model"
        << exit(FatalError);
}

const Switch projectTabulatedZRoundoff
(
    runTime.controlDict().lookupOrDefault<Switch>("projectTabulatedZRoundoff", false)
);
if (projectTabulatedZRoundoff
 && (!conserveTabulatedDensity || !reaction->compositionTabulated()))
{
    FatalErrorInFunction
        << "projectTabulatedZRoundoff requires conservative density and tabulated composition"
        << exit(FatalError);
}
scalar cumulativeZRoundoffMass=0, cumulativeZRoundoffAbsoluteMass=0;
unsigned long long cumulativeZRoundoffCells=0;

Info<< "Creating field dpdt\n" << endl;
volScalarField dpdt
(
    IOobject
    (
        "dpdt",
        runTime.timeName(),
        mesh
    ),
    mesh,
    dimensionedScalar(p.dimensions()/dimTime, 0)
);

Info<< "Creating field kinetic energy K\n" << endl;
volScalarField K("K", 0.5*magSqr(U));

#include "createFgmEnergy.H"
#include "createFgmSourceIntegration.H"

multivariateSurfaceInterpolationScheme<scalar>::fieldTable fields;

forAll(Y, i)
{
    fields.add(Y[i]);
}
fields.add(thermo.he());
if (absoluteEnthalpyFGM) fields.add(fgmAbsoluteEnthalpy());
if (reaction->progressVariable()) fields.add(*reaction->progressVariable());
if (mesh.foundObject<volScalarField>("Z"))
{
    fields.add(mesh.lookupObject<volScalarField>("Z"));
}

const Switch writeEnergyBudget
(
    runTime.controlDict().lookupOrDefault<Switch>("writeEnergyBudget", false)
);
const Switch writeEnergyResidualAudit
(
    runTime.controlDict().lookupOrDefault<Switch>("writeEnergyResidualAudit", false)
);
if (writeEnergyBudget)
{
    rho.writeOpt() = IOobject::AUTO_WRITE;
    thermo.he().writeOpt() = IOobject::AUTO_WRITE;
    Info().precision(15);
}

#include "createMRF.H"
#include "createFvOptions.H"
