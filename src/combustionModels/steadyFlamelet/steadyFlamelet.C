#include "steadyFlamelet.H"
#include "fvmSup.H"
#include "PstreamReduceOps.H"
#include "IOdictionary.H"
#include "cyclicFvPatchFields.H"
#include "Switch.H"
#include <cmath>
#include <exception>

namespace Foam { namespace combustionModels {
template<class ReactionThermo>
void steadyFlamelet<ReactionThermo>::refuse(const string& reason) const
{
    FatalErrorInFunction << "steadyFlamelet: " << reason
        << "; no clipping, progress transport or added heat source" << exit(FatalError);
}

template<class ReactionThermo>
steadyFlamelet<ReactionThermo>::steadyFlamelet
(
    const word& modelType, const ReactionThermo& thermo,
    const compressibleMomentumTransportModel& turb, const word& combustionProperties
)
:
    ThermoCombustion<ReactionThermo>(modelType, thermo, turb), table_(),
    Z_(IOobject("Z", this->mesh().time().timeName(), this->mesh(),
        IOobject::MUST_READ, IOobject::AUTO_WRITE), this->mesh()),
    c_(IOobject("c", this->mesh().time().timeName(), this->mesh(),
        IOobject::NO_READ, IOobject::AUTO_WRITE), this->mesh(),
        dimensionedScalar("zero", dimless, 0)),
    temperature_(IOobject("steadyTdiag", this->mesh().time().timeName(), this->mesh(),
        IOobject::NO_READ, IOobject::AUTO_WRITE), this->mesh(),
        dimensionedScalar("zero", dimTemperature, 0)),
    heatRelease_(IOobject("steadyQdot", this->mesh().time().timeName(), this->mesh(),
        IOobject::NO_READ, IOobject::AUTO_WRITE), this->mesh(),
        dimensionedScalar("zero", dimEnergy/dimVolume/dimTime, 0)),
    map_(), co2_(-1), co_(-1)
{
    (void)combustionProperties;
    const dictionary& control=this->mesh().time().controlDict();
    if (control.lookupOrDefault<word>("fgmEnergyForm", "") != "absoluteEnthalpy"
     || control.lookupOrDefault<word>("fgmSourceIntegration", "explicit") != "explicit"
     || control.lookupOrDefault<Switch>("fgmProgressSourceEnabled", true)
     || control.lookupOrDefault<Switch>("fgmSkipUnusedDimix", false)
     || control.lookupOrDefault<Switch>("runTimeModifiable", true))
        refuse("requires absolute Ha, no progress source/split, full diffusivity calculation and immutable controls");
    const IOdictionary momentum(IOobject("momentumTransport", this->mesh().time().constant(),
        this->mesh(), IOobject::MUST_READ, IOobject::NO_WRITE, false));
    const IOdictionary transport(IOobject("thermophysicalTransport", this->mesh().time().constant(),
        this->mesh(), IOobject::MUST_READ, IOobject::NO_WRITE, false));
    if (momentum.lookupOrDefault<word>("simulationType", "") != "laminar"
     || !transport.found("laminar")
     || transport.subDict("laminar").lookupOrDefault<word>("model", "") != "Fourier")
        refuse("only the explicit laminar delta-PDF / Fourier diagnostic is supported");
    const fileName path(this->coeffs().lookup("table"));
    if (!path.isAbsolute()) refuse("table must have an explicit absolute shared-case path");
    try { table_.reset(new forgeSteady::Table(path.c_str())); }
    catch (const std::exception& error) { refuse(error.what()); }
    const scalar fixedChi=this->coeffs().template lookup<scalar>("fixedChi");
    const word definition(this->coeffs().lookup("chiDefinition"));
    if (!std::isfinite(fixedChi) || fixedChi != table_().chi || definition != table_().chiDefinition.c_str())
        refuse("declared fixed chi/definition differs from table");
    const PtrList<volScalarField>& species=this->thermo().composition().Y();
    if (std::size_t(species.size()) != table_().species.size()) refuse("species count differs from thermodynamics");
    map_.setSize(table_().species.size(), -1);
    forAll(map_, s)
    {
        forAll(species, i) if (species[i].name() == table_().species[s].c_str()) map_[s]=i;
        if (map_[s] < 0) refuse("table species missing in thermodynamics: " + string(table_().species[s].c_str()));
        if (table_().species[s] == "CO2") co2_=s;
        if (table_().species[s] == "CO") co_=s;
    }
    if (co2_ < 0 || co_ < 0) refuse("diagnostic carbon progress requires CO2 and CO");
    Info<< "steadyFlamelet contract: fixedChi=" << fixedChi << " chiDefinition=" << definition
        << " pressurePa=" << table_().pressure << " points=" << table_().size()
        << " progressTransport=0 source=0 temperatureOwner=thermo energy=Ha"
        << " closure=laminar-delta-PDF fixedPhysicalProfile=1" << endl;
    correct();
}

template<class ReactionThermo>
void steadyFlamelet<ReactionThermo>::correct()
{
    PtrList<volScalarField>& species=const_cast<ReactionThermo&>(this->thermo()).composition().Y();
    Z_.correctBoundaryConditions();
    scalar worstSum=0, minZ=GREAT, maxZ=-GREAT;
    forAll(Z_, celli)
    {
        forgeSteady::State state;
        try { state=table_().lookup(Z_[celli]); }
        catch (const std::exception& error)
        {
            FatalErrorInFunction << "steadyFlamelet cell=" << celli << " Z=" << Z_[celli]
                << ": " << error.what() << exit(FatalError);
        }
        scalar sum=0;
        forAll(map_, s) { species[map_[s]][celli]=state.y[s]; sum+=state.y[s]; }
        worstSum=max(worstSum, mag(sum-1));
        c_[celli]=state.y[co2_]+state.y[co_];
        temperature_[celli]=state.temperature; heatRelease_[celli]=state.heatRelease;
        minZ=min(minZ,Z_[celli]); maxZ=max(maxZ,Z_[celli]);
    }
    // Preserve case BC types; refresh processor/outlet/gradient data after Y.
    forAll(species, s) species[s].correctBoundaryConditions();
    scalar worstBoundary=0;
    forAll(Z_.boundaryField(), patchi)
    {
      const bool cyclic=isA<cyclicFvPatchScalarField>(Z_.boundaryField()[patchi]);
      scalarField localZ, neighbourZ;
      if (cyclic)
      {
          const cyclicFvPatchScalarField& patch=refCast<const cyclicFvPatchScalarField>(Z_.boundaryField()[patchi]);
          localZ=patch.patchInternalField(); neighbourZ=patch.patchNeighbourField();
      }
      forAll(Z_.boundaryField()[patchi], facei)
      {
        forgeSteady::State state;
        try
        {
            state=table_().lookup(Z_.boundaryField()[patchi][facei]);
            if (cyclic)
            {
                // Coupled cyclic storage is an interpolated face value; unlike
                // processor storage, it is not the neighbour cell value.
                const forgeSteady::State owner=table_().lookup(localZ[facei]);
                const forgeSteady::State neighbour=table_().lookup(neighbourZ[facei]);
                const scalar w=Z_.boundaryField()[patchi].patch().weights()[facei];
                forAll(map_, s) state.y[s]=w*owner.y[s]+(1-w)*neighbour.y[s];
                state.temperature=w*owner.temperature+(1-w)*neighbour.temperature;
                state.heatRelease=w*owner.heatRelease+(1-w)*neighbour.heatRelease;
            }
        }
        catch (const std::exception& error)
        {
            FatalErrorInFunction << "steadyFlamelet patch=" << patchi << " face=" << facei
                << ": " << error.what() << exit(FatalError);
        }
        forAll(map_, s) worstBoundary=max(worstBoundary,
            mag(species[map_[s]].boundaryField()[patchi][facei]-state.y[s]));
        c_.boundaryFieldRef()[patchi][facei]=state.y[co2_]+state.y[co_];
        temperature_.boundaryFieldRef()[patchi][facei]=state.temperature;
        heatRelease_.boundaryFieldRef()[patchi][facei]=state.heatRelease;
      }
    }
    reduce(worstSum,maxOp<scalar>()); reduce(worstBoundary,maxOp<scalar>());
    reduce(minZ,minOp<scalar>()); reduce(maxZ,maxOp<scalar>());
    if (worstSum>1e-8 || worstBoundary>1e-8) refuse("species or boundary lookup consistency failed");
    Info<< "steadyFlamelet t=" << this->mesh().time().value()
        << " Zmin=" << minZ << " Zmax=" << maxZ << " maxSumError=" << worstSum
        << " maxBoundaryLookupError=" << worstBoundary
        << " compositionRefreshed=1 transportedProgress=0 addedHeatSource=0" << endl;
}

template<class ReactionThermo>
tmp<fvScalarMatrix> steadyFlamelet<ReactionThermo>::R(volScalarField& Y) const
{
    refuse("species equation requested from a prescribed-composition model");
    return tmp<fvScalarMatrix>(new fvScalarMatrix(Y,dimMass/dimTime));
}
template<class ReactionThermo>
tmp<volScalarField> steadyFlamelet<ReactionThermo>::Qdot() const
{
    return tmp<volScalarField>(new volScalarField(heatRelease_));
}
template<class ReactionThermo>
bool steadyFlamelet<ReactionThermo>::read()
{
    refuse("runtime reread is unsupported; freeze new inputs and start at zero");
    return false;
}
}}
