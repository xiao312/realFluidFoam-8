#include "relaxedTable.H"
#include "fvmSup.H"
#include "PstreamReduceOps.H"
#include "IOdictionary.H"
#include "Switch.H"
#include "fgmDimixPolicy.H"
#include "endpointCoordinate.H"
#include "relaxationClock.H"
#include <cmath>
#include <exception>

namespace Foam { namespace combustionModels {
template<class ReactionThermo>
void relaxedTable<ReactionThermo>::refuse(const string& reason) const
{
    FatalErrorInFunction << "relaxedTable: " << reason
        << "; no target fitting, source clipping or species normalization"
        << exit(FatalError);
}

template<class ReactionThermo>
relaxedTable<ReactionThermo>::relaxedTable
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
    heatRelease_(IOobject("relaxedTableQdot", this->mesh().time().timeName(), this->mesh(),
        IOobject::NO_READ, IOobject::AUTO_WRITE), this->mesh(),
        dimensionedScalar("zero", dimEnergy/dimVolume/dimTime, 0)),
    map_(), targets_(), formationEnthalpy_(), relaxationSteps_(0),
    allowEndpointRoundoff_(false), co2_(-1), co_(-1)
{
    (void)combustionProperties;
    const dictionary& control = this->mesh().time().controlDict();
    if (control.lookupOrDefault<word>("fgmEnergyForm", "") != "absoluteEnthalpy"
        || control.lookupOrDefault<word>("fgmSourceIntegration", "explicit") != "explicit"
        || control.lookupOrDefault<Switch>("fgmProgressSourceEnabled", true)
        || control.lookupOrDefault<Switch>("runTimeModifiable", true))
        refuse("requires absolute Ha, no progress source/split and immutable controls");
    const word ddt(this->mesh().ddtScheme("ddt(rho,Yi)"));
    if (ddt != "Euler") refuse("source predictor requires global Euler species transport");
    validateFgmDimixSuppression(this->mesh());
    const IOdictionary momentum(IOobject("momentumTransport", this->mesh().time().constant(),
        this->mesh(), IOobject::MUST_READ, IOobject::NO_WRITE, false));
    const IOdictionary transport(IOobject("thermophysicalTransport", this->mesh().time().constant(),
        this->mesh(), IOobject::MUST_READ, IOobject::NO_WRITE, false));
    if (momentum.lookupOrDefault<word>("simulationType", "") != "laminar"
        || !transport.found("laminar")
        || transport.subDict("laminar").lookupOrDefault<word>("model", "") != "Fourier")
        refuse("initial qualification requires laminar Fourier unity-Lewis transport");
    const RelaxationClock clock = relaxedTableClock
        (this->coeffs(), this->mesh().time().deltaTValue());
    // Keep the existing class layout. In fixed-time mode this is an initial
    // effective step count; each update uses the actual executing timestep.
    relaxationSteps_ = 1/clock.alpha;
    const word policy(this->coeffs().template lookupOrDefault<word>("lookupRoundoffPolicy", "strict"));
    if (policy != "strict" && policy != "endpoint64epsilon") refuse("unknown endpoint policy");
    allowEndpointRoundoff_ = policy == "endpoint64epsilon";
    const fileName file(this->coeffs().lookup("table"));
    if (!file.isAbsolute()) refuse("table path must be absolute and case-owned");
    try { table_.reset(new forgeSteady::Table(file.c_str())); }
    catch (const std::exception& error) { refuse(error.what()); }
    const PtrList<volScalarField>& species = this->thermo().composition().Y();
    if (std::size_t(species.size()) != table_().species.size()) refuse("species inventory differs");
    map_.setSize(species.size(), -1);
    targets_.setSize(species.size());
    formationEnthalpy_.setSize(species.size(), scalar(0));
    forAll(map_, s)
    {
        forAll(species, i) if (species[i].name() == table_().species[s].c_str()) map_[s] = i;
        if (map_[s] < 0) refuse("table species missing from executing thermo");
        targets_[s].setSize(this->mesh().nCells(), scalar(0));
        formationEnthalpy_[s] = this->thermo().composition().Hf(map_[s]);
        if (table_().species[s] == "CO2") co2_ = s;
        if (table_().species[s] == "CO") co_ = s;
    }
    if (co2_ < 0 || co_ < 0) refuse("carbon diagnostic requires CO and CO2");
    Info<< "relaxedTable contract: Cr=" << relaxationSteps_
        << " alpha=" << clock.alpha << " mode=" << clock.mode << " tau_s=" << clock.time
        << " actualSpeciesTransport=1 targetTemperatureDiagnosticOnly=1"
        << " sourceAfterPureMixing=1 energy=absoluteHa addedEnergySource=0"
        << " targetChiLabel=" << table_().chi << endl;
    correct();
    c_ == species[map_[co2_]] + species[map_[co_]];
}

template<class ReactionThermo>
void relaxedTable<ReactionThermo>::correct()
{
    Z_.correctBoundaryConditions();
    scalar minimum = GREAT, maximum = -GREAT;
    label nonfinite = 0;
    forAll(Z_, celli)
    {
        if (!std::isfinite(Z_[celli])) ++nonfinite;
        minimum = min(minimum, Z_[celli]); maximum = max(maximum, Z_[celli]);
    }
    reduce(minimum, minOp<scalar>()); reduce(maximum, maxOp<scalar>());
    reduce(nonfinite, sumOp<label>());
    Info<< "relaxedTableTargetInput t=" << this->mesh().time().value()
        << " rawMinZ=" << minimum << " rawMaxZ=" << maximum
        << " nonfinite=" << nonfinite << endl;
    if (nonfinite) refuse("nonfinite transported Z");
    forAll(Z_, celli)
    {
        try
        {
            const auto coordinate = forgeSteady::endpointCoordinate(Z_[celli], allowEndpointRoundoff_);
            const forgeSteady::State state = table_().lookup(coordinate.value);
            forAll(map_, s) targets_[s][celli] = state.y[s];
            temperature_[celli] = state.temperature;
        }
        catch (const std::exception& error) { refuse(error.what()); }
    }
    // This field is diagnostic only; actual species patches remain case-owned.
    forAll(Z_.boundaryField(), patchi) forAll(Z_.boundaryField()[patchi], facei)
    {
        try
        {
            const auto coordinate = forgeSteady::endpointCoordinate
                (Z_.boundaryField()[patchi][facei], allowEndpointRoundoff_);
            temperature_.boundaryFieldRef()[patchi][facei] = table_().lookup(coordinate.value).temperature;
        }
        catch (const std::exception& error) { refuse(error.what()); }
    }
}

template<class ReactionThermo>
void relaxedTable<ReactionThermo>::correctSpeciesAfterTransport()
{
    PtrList<volScalarField>& species =
        const_cast<ReactionThermo&>(this->thermo()).composition().Y();
    const scalar dt = this->mesh().time().deltaTValue();
    const RelaxationClock clock = relaxedTableClock(this->coeffs(), dt);
    const scalar alpha = clock.alpha;
    const volScalarField& density = this->rho();
    scalar worstSum = 0, minimum = GREAT, largestUpdate = 0, largestElementChange = 0;
    scalarField delta(map_.size(), scalar(0));
    heatRelease_ = dimensionedScalar("zero", dimEnergy/dimVolume/dimTime, 0);
    forAll(Z_, celli)
    {
        scalar sum = 0, chemicalChange = 0;
        forAll(map_, s)
        {
            const scalar before = species[map_[s]][celli];
            const scalar after = (1-alpha)*before + alpha*targets_[s][celli];
            if (!std::isfinite(after)) refuse("nonfinite species update");
            delta[s] = after-before;
            species[map_[s]][celli] = after;
            sum += after; minimum = min(minimum, after);
            largestUpdate = max(largestUpdate, mag(delta[s]));
            chemicalChange += formationEnthalpy_[s]*delta[s];
        }
        worstSum = max(worstSum, mag(sum-1));
        for (const auto& coefficient : table_().elementCoefficients())
        {
            scalar change = 0;
            forAll(map_, s) change += coefficient[s]*delta[s];
            largestElementChange = max(largestElementChange, mag(change));
        }
        heatRelease_[celli] = -density[celli]*chemicalChange/dt;
    }
    forAll(species, i) species[i].correctBoundaryConditions();
    c_ == species[map_[co2_]] + species[map_[co_]];
    reduce(worstSum, maxOp<scalar>()); reduce(minimum, minOp<scalar>());
    reduce(largestUpdate, maxOp<scalar>()); reduce(largestElementChange, maxOp<scalar>());
    Info<< "relaxedTableSource t=" << this->mesh().time().value()
        << " Cr=" << 1/alpha << " alpha=" << alpha << " tau_s=" << clock.time
        << " relaxationMode=" << clock.mode
        << " maxDeltaY=" << largestUpdate << " maxSumError=" << worstSum
        << " minY=" << minimum << " maxElementChange=" << largestElementChange
        << " sourceElementAudit=reportOnly addedEnergySource=0 oldTimeModified=0" << endl;
    if (worstSum > 1e-8 || minimum < 0) refuse("species positivity/sum check failed after relaxation");
}

template<class ReactionThermo>
tmp<fvScalarMatrix> relaxedTable<ReactionThermo>::R(volScalarField& Y) const
{
    // The predictor is pure mixing. The explicit source is applied afterward,
    // not also assembled here; every PIMPLE predictor starts from old-time Y.
    return tmp<fvScalarMatrix>(new fvScalarMatrix(Y, dimMass/dimTime));
}

template<class ReactionThermo>
tmp<volScalarField> relaxedTable<ReactionThermo>::Qdot() const
{
    return tmp<volScalarField>(new volScalarField(heatRelease_));
}

template<class ReactionThermo>
bool relaxedTable<ReactionThermo>::read()
{
    refuse("runtime reread unsupported; freeze new inputs and start at zero");
    return false;
}
}}
