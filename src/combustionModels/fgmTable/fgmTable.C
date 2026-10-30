/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  8
     \\/     M anipulation  |
-------------------------------------------------------------------------------
License
    This file is part of OpenFOAM.

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by the
    Free Software Foundation, either version 3 of the License, or (at your
    option) any later version.

    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

\*---------------------------------------------------------------------------*/

#include "fgmTable.H"
#include "fvmSup.H"
#include "error.H"
#include "OSspecific.H"
#include "PstreamReduceOps.H"

#include <string>


// * * * * * * * * * * * * * Private Member Functions  * * * * * * * * * * * //

template<class ReactionThermo>
Foam::fileName
Foam::combustionModels::fgmTable<ReactionThermo>::resolveTablePath() const
{
    const fileName given(this->coeffs().lookup("table"));

    if (given.isAbsolute())
    {
        return given;
    }

    // A table is a case input, so which file is read must not depend on the
    // process working directory.  Run B of job 126044464 proved the dependence
    // is real: the solver was given `-case /abs/path`, the table was present in
    // that case's constant/ directory, and the reader refused
    // 'constant/linear.tbl' because Time::constant() was itself relative to the
    // working directory, which was elsewhere.  So the case root is built from
    // rootPath()/caseName() and every candidate is tried and can be named.
    const Time& runTime = this->mesh().time();

    fileName caseRoot(runTime.rootPath());
    if (runTime.caseName().isAbsolute())
    {
        caseRoot = runTime.caseName();
    }
    else if (runTime.caseName() != ".")
    {
        caseRoot = caseRoot/runTime.caseName();
    }

    DynamicList<fileName> candidates(3);
    candidates.append(caseRoot/"constant"/given);
    candidates.append(runTime.constant()/given);
    candidates.append(given);

    forAll(candidates, i)
    {
        if (exists(candidates[i]))
        {
            return candidates[i];
        }
    }

    std::string tried;
    forAll(candidates, i)
    {
        tried += "    " + candidates[i].name() + "\n";
    }

    FatalErrorInFunction
        << "no FGM table '" << given.c_str() << "' under the case root" << nl
        << tried.c_str()
        << "cwd is '" << Foam::cwd().c_str() << "'; the table is refused; "
        << "nothing is clamped, rescaled or repaired."
        << Foam::abort(FatalError);

    return given;
}


template<class ReactionThermo>
Foam::fgm::fgmTableReader::boundsPolicy
Foam::combustionModels::fgmTable<ReactionThermo>::resolveBoundsPolicy() const
{
    const word policy
    (
        this->coeffs().template lookupOrDefault<word>("boundsPolicy", "error")
    );

    if (policy == "error")
    {
        return fgm::fgmTableReader::ERROR_ON_BOUNDS;
    }

    if (policy == "clamp")
    {
        return fgm::fgmTableReader::CLAMP_TO_BOUNDS;
    }

    refuse("boundsPolicy '" + policy + "' is not 'error' or 'clamp'");

    return fgm::fgmTableReader::ERROR_ON_BOUNDS;
}


template<class ReactionThermo>
void Foam::combustionModels::fgmTable<ReactionThermo>::refuse
(
    const string& reason
) const
{
    FatalErrorInFunction
        << "fgmTable: " << reason << nl
        << "Contract: the table supplies composition and progress source only; "
        << "density, temperature and enthalpy remain with the thermophysical "
        << "model.  Nothing is clamped or rescaled." << nl
        << abort(FatalError);
}


template<class ReactionThermo>
void Foam::combustionModels::fgmTable<ReactionThermo>::buildSpeciesMap()
{
    const wordList& tableSpecies = table_().species();
    const PtrList<volScalarField>& Y =
        this->thermo().composition().Y();

    labelList map(tableSpecies.size(), -1);

    forAll(tableSpecies, s)
    {
        bool found = false;
        forAll(Y, i)
        {
            if (Y[i].name() == tableSpecies[s])
            {
                map[s] = i;
                found = true;
                break;
            }
        }

        if (!found)
        {
            refuse
            (
                "table species '" + tableSpecies[s]
              + "' is not present in the thermophysical mixture"
            );
        }
    }

    forAll(Y, i)
    {
        bool found = false;
        forAll(tableSpecies, s)
        {
            if (tableSpecies[s] == Y[i].name())
            {
                found = true;
                break;
            }
        }

        if (!found)
        {
            refuse
            (
                "thermophysical species '" + Y[i].name()
              + "' has no block in the table; the tabulated composition must "
                "cover every species of the mixture"
            );
        }
    }

    tableToThermo_ = map;
}


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

template<class ReactionThermo>
Foam::combustionModels::fgmTable<ReactionThermo>::fgmTable
(
    const word& modelType,
    const ReactionThermo& thermo,
    const compressibleMomentumTransportModel& turb,
    const word& combustionProperties
)
:
    ThermoCombustion<ReactionThermo>(modelType, thermo, turb),
    table_(new fgm::fgmTableReader(resolveTablePath(), resolveBoundsPolicy())),
    ZName_(this->coeffs().template lookupOrDefault<word>("mixtureFractionField", "Z")),
    cName_(this->coeffs().template lookupOrDefault<word>("progressField", "c")),
    Z_
    (
        IOobject
        (
            ZName_,
            this->mesh().time().timeName(),
            this->mesh(),
            IOobject::MUST_READ,
            IOobject::AUTO_WRITE
        ),
        this->mesh()
    ),
    c_
    (
        IOobject
        (
            cName_,
            this->mesh().time().timeName(),
            this->mesh(),
            IOobject::MUST_READ,
            IOobject::AUTO_WRITE
        ),
        this->mesh()
    ),
    Sc_
    (
        IOobject
        (
            "fgmSc",
            this->mesh().time().timeName(),
            this->mesh(),
            IOobject::NO_READ,
            IOobject::AUTO_WRITE
        ),
        this->mesh(),
        dimensionedScalar("fgmSc", dimMass/dimVolume/dimTime, scalar(0))
    ),
    ScSource_
    (
        IOobject
        (
            "fgmScSource",
            this->mesh().time().timeName(),
            this->mesh(),
            IOobject::NO_READ,
            IOobject::AUTO_WRITE
        ),
        this->mesh(),
        dimensionedScalar
        (
            "fgmScSource", dimMass/dimVolume/dimTime, scalar(0)
        )
    ),
    Qdot_
    (
        IOobject
        (
            "fgmQdot",
            this->mesh().time().timeName(),
            this->mesh(),
            IOobject::NO_READ,
            IOobject::AUTO_WRITE
        ),
        this->mesh(),
        dimensionedScalar("fgmQdot", dimEnergy/dimVolume/dimTime, scalar(0))
    ),
    Tdiag_
    (
        IOobject
        (
            "fgmTdiag",
            this->mesh().time().timeName(),
            this->mesh(),
            IOobject::NO_READ,
            IOobject::AUTO_WRITE
        ),
        this->mesh(),
        dimensionedScalar("fgmTdiag", dimTemperature, scalar(0))
    ),
    speciesSumLimit_
    (
        this->coeffs().template lookupOrDefault<scalar>("speciesSumLimit", 1e-8)
    ),
    worstCellSum_(0),
    nCorrect_(0)
{
    // The combustion properties word is consumed by the base selector; the
    // model reads only its own subdictionary.
    (void)combustionProperties;

    buildSpeciesMap();

    Info<< typeName << ": loaded" << nl;
    table_().writeSummary(Info);

    Info<< typeName
        << ": fields Z=" << ZName_ << " c=" << cName_
        << " -> fgmSc [kg/m3/s, table block for Yc], fgmScSource [kg/m3/s, "
           "source of the transported coordinate], fgmQdot [W/m3], fgmTdiag "
           "[K; diagnostic only]"
        << nl
        << typeName
        << ": progress coordinate=" << table_().progressCoordinate().c_str()
        << " dYc=" << table_().progressDYc()
        << " (source of c = table Sc/dYc when normalised)"
        << nl
        << typeName
        << ": density, temperature and enthalpy are owned by "
        << thermo.type() << ", not by this model" << nl << endl;

    // Fill the table-derived fields once, so that a run that never reaches a
    // time loop still leaves a written, checkable state.
    correct();
}


// * * * * * * * * * * * * * * * * Destructor  * * * * * * * * * * * * * * * //

template<class ReactionThermo>
Foam::combustionModels::fgmTable<ReactionThermo>::~fgmTable()
{}


// * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * * //

template<class ReactionThermo>
void Foam::combustionModels::fgmTable<ReactionThermo>::correct()
{
    const fgm::fgmTableReader& table = table_();

    PtrList<volScalarField>& Y =
        const_cast<ReactionThermo&>(this->thermo()).composition().Y();

    scalarField Ylookup;
    scalar Sc = 0;
    scalar Q = 0;
    scalar Td = 0;

    scalar worstSum = 0;
    scalar minZ = 0, maxZ = 0, minC = 0, maxC = 0;
    scalar minSc = 0, maxSc = 0, minQ = 0, maxQ = 0;
    scalar minScSource = 0, maxScSource = 0;

    forAll(Z_, celli)
    {
        table.lookup(Z_[celli], c_[celli], Ylookup, Sc, Q, Td);

        forAll(tableToThermo_, s)
        {
            Y[tableToThermo_[s]][celli] = Ylookup[s];
        }

        Sc_[celli] = Sc;
        ScSource_[celli] = table.sourceOfC(Sc);
        Qdot_[celli] = Q;        Tdiag_[celli] = Td;

        scalar sum = 0;
        forAll(Ylookup, s)
        {
            sum += Ylookup[s];
        }
        worstSum = max(worstSum, mag(sum - 1));

        if (celli == 0)
        {
            minZ = maxZ = Z_[celli];
            minC = maxC = c_[celli];
            minSc = maxSc = Sc;
            minScSource = maxScSource = ScSource_[celli];
            minQ = maxQ = Q;
        }
        else
        {
            minZ = min(minZ, Z_[celli]);
            maxZ = max(maxZ, Z_[celli]);
            minC = min(minC, c_[celli]);
            maxC = max(maxC, c_[celli]);
            minSc = min(minSc, Sc);
            maxSc = max(maxSc, Sc);
            minScSource = min(minScSource, ScSource_[celli]);
            maxScSource = max(maxScSource, ScSource_[celli]);
            minQ = min(minQ, Q);
            maxQ = max(maxQ, Q);
        }
    }

    // Species equations are skipped in tabulated mode, so their ordinary
    // solve() boundary update never runs. Refresh coupled/outlet/gradient
    // patches after replacing internal composition; preserve case-fixed inlets.
    forAll(Y, s) Y[s].correctBoundaryConditions();

    scalar lookupCount = table.lookupCount();
    scalar clipCount = table.clipCount();
    scalar maxCExcursion = table.maxProgressExcursion();
    scalar maxZExcursion = table.maxZExcursion();
    reduce(lookupCount, sumOp<scalar>());
    reduce(clipCount, sumOp<scalar>());
    reduce(maxCExcursion, maxOp<scalar>());
    reduce(maxZExcursion, maxOp<scalar>());
    Info<< "fgmBounds cumulativeLookups=" << lookupCount
        << " cumulativeCorrections=" << clipCount
        << " maxProgressExcursion=" << maxCExcursion
        << " maxZExcursion=" << maxZExcursion << endl;

    worstCellSum_ = max(worstCellSum_, worstSum);
    ++nCorrect_;

    if (worstCellSum_ > speciesSumLimit_)
    {
        refuse
        (
            "tabulated composition does not sum to one (worst |sum(Y)-1| = "
          + std::to_string(worstCellSum_) + " > limit "
          + std::to_string(speciesSumLimit_) + ")"
        );
    }

    Info<< typeName << ": cells " << Z_.size()
        << " Z[" << minZ << ", " << maxZ << "]"
        << " c[" << minC << ", " << maxC << "]"
        << " Sc[" << minSc << ", " << maxSc << "] kg/m3/s"
        << " ScSource[" << minScSource << ", " << maxScSource << "] kg/m3/s"
        << " Qdot[" << minQ << ", " << maxQ << "] W/m3"
        << " worst|sumY-1| " << worstCellSum_
        << endl;
}


template<class ReactionThermo>
Foam::tmp<Foam::fvScalarMatrix>
Foam::combustionModels::fgmTable<ReactionThermo>::R
(
    volScalarField& Y
) const
{
    // A tabulated composition is prescribed, not solved.  This matrix is empty
    // so that a solver which ignores compositionTabulated() gets a visibly
    // unsourced species equation rather than a silently wrong one; the
    // supported path is that the solver skips the species equations.
    tmp<fvScalarMatrix> tSu(new fvScalarMatrix(Y, dimMass/dimTime));

    return tSu;
}


template<class ReactionThermo>
Foam::tmp<Foam::volScalarField>
Foam::combustionModels::fgmTable<ReactionThermo>::progressSource() const
{
    // kg/(m3 s) of the transported coordinate.  The table's block is the source
    // of the composition progress variable Yc; when the c axis is normalized the
    // source of c is that block divided by dYc, and the division happens here or
    // not at all.  No density multiplication: the table already carries a
    // volumetric rate, and applying rho here would be the double counting the
    // interface contract forbids.
    return tmp<volScalarField>(new volScalarField(ScSource_));
}


template<class ReactionThermo>
Foam::tmp<Foam::volScalarField>
Foam::combustionModels::fgmTable<ReactionThermo>::Qdot() const
{
    return tmp<volScalarField>(new volScalarField(Qdot_));
}


template<class ReactionThermo>
bool Foam::combustionModels::fgmTable<ReactionThermo>::read()
{
    if (ThermoCombustion<ReactionThermo>::read())
    {
        table_.reset
        (
            new fgm::fgmTableReader(resolveTablePath(), resolveBoundsPolicy())
        );

        speciesSumLimit_ =
            this->coeffs().template lookupOrDefault<scalar>("speciesSumLimit", 1e-8);

        buildSpeciesMap();

        Info<< typeName << ": re-read" << nl;
        table_().writeSummary(Info);

        return true;
    }

    return false;
}


// ************************************************************************* //
