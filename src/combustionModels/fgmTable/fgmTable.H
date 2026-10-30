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

Class
    Foam::combustionModels::fgmTable

Description
    Tabulated FGM combustion model for a real-fluid-capable solver.

    The model owns exactly three things: the tabulated composition, the
    tabulated progress-variable source, and the tabulated heat release.  It
    does **not** own density, temperature or enthalpy.  Those stay with the
    thermophysical model, which inverts them from the equation of state and the
    energy variable it is configured with.  Nothing in this class computes
    ``rho = p*W/(R*T)``, nothing reconstructs an enthalpy from the table, and
    nothing multiplies a tabulated source by a density: the source is read in
    kg/(m3 s) and inserted as such.

    Inputs, read from the case:

    * ``Z``  mixture fraction, advected by the solver, tabulated coordinate 1
    * ``c``  progress variable, advected by the solver under ``fgm::Sc``,
             tabulated coordinate 2

    Outputs, written every ``correct()``:

    * the species mass fractions of the thermophysical mixture, overwritten
      from the table (so species equations must not also be solved; the base
      class reports ``compositionTabulated()`` for the solver to guard on)
    * ``Sc``    progress source [kg/m3/s]
    * ``Qdot``  heat release rate [W/m3]
    * ``Tdiag`` tabulated temperature, diagnostic only, never fed back

    The table format and the ownership contract are documented in
    ``replication/docs/fgm-of8-interface-contract.md``.

SourceFiles
    fgmTable.C
    fgmTables.C

\*---------------------------------------------------------------------------*/

#ifndef fgmTable_H
#define fgmTable_H

#include "ThermoCombustion.H"
#include "fgmTableReader.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{
namespace combustionModels
{

/*---------------------------------------------------------------------------*\
                        Class fgmTable Declaration
\*---------------------------------------------------------------------------*/

template<class ReactionThermo>
class fgmTable
:
    public ThermoCombustion<ReactionThermo>
{
private:

    // Private data

        //- Tabulated chemistry: reader and interpolator
        autoPtr<fgm::fgmTableReader> table_;

        //- Mixture fraction field name
        word ZName_;

        //- Progress variable field name
        word cName_;

        //- Mixture fraction
        volScalarField Z_;

        //- Progress variable
        volScalarField c_;

        //- Tabulated progress source of the composition variable Yc, the block
        //  the table carries verbatim [kg/(m3/s)]; never inserted into an
        //  equation, because the transported coordinate may be normalized
        volScalarField Sc_;

        //- Volumetric source of the *transported* progress coordinate
        //  [kg/m3/s]: Sc_ for a mass-fraction coordinate and Sc_/dYc for a
        //  normalized one.  This is the single place the table's normalization
        //  enters the solver, and it is the field progressSource() returns.
        volScalarField ScSource_;

        //- Tabulated heat release rate [W/m3]
        volScalarField Qdot_;

        //- Tabulated diagnostic temperature [K]
        volScalarField Tdiag_;

        //- Species-sum refusal limit, from the table contract (default 1e-8)
        scalar speciesSumLimit_;

        //- Table species index -> thermophysical species index
        labelList tableToThermo_;

        //- Worst |sum(Y) - 1| seen in a cell over the life of the run
        scalar worstCellSum_;

        //- Number of correct() calls
        label nCorrect_;


    // Private Member Functions

        //- Absolute path of the table, resolving a relative path against the
        //  case's constant directory
        fileName resolveTablePath() const;

        //- Bounds policy from the model dictionary
        fgm::fgmTableReader::boundsPolicy resolveBoundsPolicy() const;

        //- Map table species onto the thermophysical mixture, refusing any
        //  mismatch in either direction
        void buildSpeciesMap();

        //- Refuse with a message naming the contract that was broken
        void refuse(const string& reason) const;


public:

    //- Runtime type information
    TypeName("fgmTable");


    // Constructors

        //- Construct from components
        fgmTable
        (
            const word& modelType,
            const ReactionThermo& thermo,
            const compressibleMomentumTransportModel& turb,
            const word& combustionProperties
        );

        //- Disallow default bitwise copy construction
        fgmTable(const fgmTable&) = delete;


    //- Destructor
    virtual ~fgmTable();


    // Member Functions

        //- Update the composition, the source and the heat release from the
        //  table at the current (Z, c)
        virtual void correct();

        //- Species source for a species equation; empty, because a tabulated
        //  composition prescribes the species rather than solving them
        virtual tmp<fvScalarMatrix> R(volScalarField& Y) const;

        //- Heat release rate [W/m3], read from the table, never reconstructed
        virtual tmp<volScalarField> Qdot() const;

        //- The composition is prescribed by the table, so species equations
        //  must be skipped rather than solved with a zero source
        virtual bool compositionTabulated() const
        {
            return true;
        }

        //- The progress variable is transported by the solver
        virtual bool transportsProgress() const
        {
            return true;
        }

        //- The progress variable the solver transports
        virtual volScalarField* progressVariable()
        {
            return &c_;
        }

        //- Progress-variable source [kg/m3/s], tabulated, divided by dYc when
        //  the table declares a normalized coordinate so that it is the source
        //  of the variable the solver actually transports
        virtual tmp<volScalarField> progressSource() const;

        //- Tabulated source of the composition progress variable Yc, exactly as
        //  the table block states it [kg/m3/s]
        const volScalarField& Sc() const
        {
            return Sc_;
        }

        //- Source of the transported progress coordinate [kg/m3/s]
        const volScalarField& ScSource() const
        {
            return ScSource_;
        }

        //- Progress variable
        const volScalarField& c() const
        {
            return c_;
        }

        //- Mixture fraction
        const volScalarField& Z() const
        {
            return Z_;
        }

        //- Tabulated diagnostic temperature [K]
        const volScalarField& Tdiag() const
        {
            return Tdiag_;
        }

        //- Update properties from given dictionary
        virtual bool read();


    // Member Operators

        //- Disallow default bitwise assignment
        void operator=(const fgmTable&) = delete;
};


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

} // End namespace combustionModels
} // End namespace Foam

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#ifdef NoRepository
    #include "fgmTable.C"
#endif

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#endif

// ************************************************************************* //
