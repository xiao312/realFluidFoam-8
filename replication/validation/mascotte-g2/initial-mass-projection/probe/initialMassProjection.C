// Original-zero diagnostic. No time loop or thermodynamic field writes.
#include "fvCFD.H"
#include "psiReactionThermo.H"
#include <fstream>
#include <iomanip>
#include <cmath>

using namespace Foam;

static scalar divergenceL1(const surfaceScalarField& phi, const fvMesh& mesh)
{
    return gSum(mag(fvc::div(phi)().primitiveField())*mesh.V());
}

int main(int argc, char *argv[])
{
    argList::addBoolOption("apply", "Project fresh original-zero U/phi only");
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    if (!args.optionFound("apply"))
    {
        Info<< "Read-only: cells=" << mesh.nCells() << "; use -apply" << endl;
        return 0;
    }
    if (Pstream::parRun() || runTime.value() != 0 || !std::getenv("SLURM_JOB_ID"))
        FatalErrorInFunction << "Serial original zero inside Slurm required" << exit(FatalError);
    if (isFile(runTime.path()/"0"/"phi"))
        FatalErrorInFunction << "Existing phi must not be overwritten" << exit(FatalError);

    autoPtr<psiReactionThermo> model(psiReactionThermo::New(mesh));
    volScalarField rho(IOobject("rho", "0", mesh), model().rho());
    forAll(rho, celli)
        if (!std::isfinite(rho[celli]) || rho[celli] <= 0)
            FatalErrorInFunction << "Invalid executing density in cell " << celli << exit(FatalError);
    volVectorField U(IOobject("U", "0", mesh, IOobject::MUST_READ), mesh);
    surfaceScalarField phi
    (
        IOobject("phi", "0", mesh, IOobject::NO_READ),
        linearInterpolate(rho*U) & mesh.Sf()
    );
    U.correctBoundaryConditions();
    phi = linearInterpolate(rho*U) & mesh.Sf();
    const scalar before = divergenceL1(phi, mesh);
    const scalar energyBefore = gSum(0.5*rho.primitiveField()*magSqr(U.primitiveField())*mesh.V());

    wordList patchTypes(mesh.boundary().size(), "zeroGradient");
    label outlets = 0;
    forAll(patchTypes, patchi)
    {
        const fvPatch& patch = mesh.boundary()[patchi];
        if (polyPatch::constraintType(patch.type())) patchTypes[patchi] = patch.type();
        else if (patch.name() == "outlet") { patchTypes[patchi] = "fixedValue"; ++outlets; }
    }
    if (outlets != 1)
        FatalErrorInFunction << "One explicit outlet patch required" << exit(FatalError);
    volScalarField potential
    (
        IOobject("initialMassPotential", "0", mesh), mesh,
        dimensionedScalar("zero", dimArea/dimTime, 0), patchTypes
    );
    mesh.setFluxRequired(potential.name());
    dictionary controls;
    controls.add("solver", word("PCG"));
    controls.add("preconditioner", word("DIC"));
    controls.add("tolerance", scalar(1e-13));
    controls.add("relTol", scalar(0));
    controls.add("maxIter", label(20000));
    // Defect corrections retain non-orthogonal face contributions.
    for (label pass = 0; pass < 8; ++pass)
    {
        potential = dimensionedScalar("zero", dimArea/dimTime, 0);
        fvScalarMatrix equation
        (
            -fvm::laplacian(rho, potential, "laplacian(rho,initialMassPotential)")
         == -fvc::div(phi)
        );
        equation.solve(controls);
        phi += equation.flux();
        Info<< "initialMassProjection pass=" << pass << " divergenceKg_s=" << divergenceL1(phi,mesh) << endl;
    }
    scalar net = 0, inward = 0;
    forAll(phi.boundaryField(), patchi)
    {
        if (polyPatch::constraintType(mesh.boundary()[patchi].type())) continue;
        const fvsPatchScalarField& flux = phi.boundaryField()[patchi];
        net += gSum(flux);
        forAll(flux, facei) inward += max(-flux[facei], scalar(0));
        Info<< "initialMassProjection patch=" << mesh.boundary()[patchi].name()
            << " outwardKg_s=" << gSum(flux) << endl;
    }
    const scalar after = divergenceL1(phi,mesh);
    if (!std::isfinite(after) || !std::isfinite(net) || inward <= VSMALL
        || after/inward > 1e-8 || mag(net)/inward > 1e-8)
        FatalErrorInFunction << "Projection failed: divergence=" << after
            << ", net=" << net << ", inward=" << inward << exit(FatalError);
    U = fvc::reconstruct(phi/fvc::interpolate(rho));
    U.correctBoundaryConditions();
    const scalar maxSpeed = gMax(mag(U.primitiveField()));
    if (!std::isfinite(maxSpeed))
        FatalErrorInFunction << "Nonfinite projected velocity" << exit(FatalError);
    const scalar reconstruction = gSum(mag((linearInterpolate(rho*U)&mesh.Sf())-phi)().primitiveField());
    const scalar energyAfter = gSum(0.5*rho.primitiveField()*magSqr(U.primitiveField())*mesh.V());
    IOstream::defaultPrecision(17);
    U.write(); phi.write();
    std::ofstream report((runTime.path()/"initial-mass-projection-metrics.json").c_str());
    report << std::setprecision(17)
        << "{\"CFD_steps\":0,\"divergenceBefore_kg_s\":" << before
        << ",\"divergenceAfter_kg_s\":" << after << ",\"inward_kg_s\":" << inward
        << ",\"netBoundary_kg_s\":" << net << ",\"maxSpeed_m_s\":" << maxSpeed
        << ",\"kineticBefore_J\":" << energyBefore << ",\"kineticAfter_J\":" << energyAfter
        << ",\"internalFaceReconstructionL1_kg_s\":" << reconstruction
        << ",\"scientificAcceptance\":false}\n";
    if (!report.good()) FatalErrorInFunction << "Metrics write failed" << exit(FatalError);
    return 0;
}
