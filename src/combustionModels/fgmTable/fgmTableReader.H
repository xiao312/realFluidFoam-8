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
    Foam::fgm::fgmTableReader

Description
    Reader and bilinear interpolator for the campaign's FGM table format
    (schema ``forge-fgm-table-v1``), documented in
    ``replication/docs/fgm-of8-interface-contract.md``.

    The reader is deliberately strict.  Every defect it can detect is a table
    defect and is a fatal error at construction, so a table can never reach a
    time loop carrying a wrong grid size, a non-monotone coordinate, species
    that do not sum to one, a negative mass fraction, a missing block, or an
    undefined unit.  Nothing is clamped, rescaled or repaired here.

    The reader holds no physics and makes no assumption about which quantity is
    the owner of density, temperature or enthalpy; those are declared by the
    table header and enforced by the combustion model that consumes it.

SourceFiles
    fgmTableReader.C

\*---------------------------------------------------------------------------*/

#ifndef fgm_fgmTableReader_H
#define fgm_fgmTableReader_H

#include "fileName.H"
#include "wordList.H"
#include "scalarField.H"
#include "dictionary.H"
#include "fgmSourceOde.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{
namespace fgm
{

/*---------------------------------------------------------------------------*\
                       Class fgmTableReader Declaration
\*---------------------------------------------------------------------------*/

class fgmTableReader
{
public:

    //- How a value outside the tabulated grid is treated.  ``error`` is the
    //  default and the only policy admitted without an explicit choice.
    enum boundsPolicy
    {
        ERROR_ON_BOUNDS = 0,
        CLAMP_TO_BOUNDS = 1
    };


private:

    // Private data

        //- Path of the table file
        fileName path_;

        //- Provenance string carried from the header, never invented here
        string source_;

        //- sha256 of the flamelet/profile the table was built from, or "none"
        string profileSha256_;

        //- Explicit table version; v1 semantics remain unchanged.
        string schema_;

        //- Species names in table order
        wordList species_;

        //- Grid sizes
        label nZ_;
        label nC_;

        //- Grids, strictly increasing
        scalarField z_;
        scalarField c_;

        //- Mass fractions, one flat field per species, index i*nC_ + j
        List<scalarField> Y_;

        //- Progress-variable source [kg/m3/s], flat
        scalarField Sc_;

        //- Heat release [W/m3], flat
        scalarField Q_;

        //- Diagnostic temperature, flat; empty when absent
        scalarField Tdiag_;

        //- Worst |sum(Y) - 1| over the nodes, measured not repaired
        scalar worstSpeciesSum_;

        //- Bounds policy
        boundsPolicy policy_;

        //- Progress coordinate declaration from the header: "mass-fraction"
        //  when the c axis is the composition progress variable itself, or
        //  "normalised" when it is (Yc - Yc_min)/dYc.  Never defaulted: a
        //  table that does not say is refused, because the source of c then
        //  differs from the tabulated Sc by an unknown factor.
        string progressCoordinate_;

        //- Normalization width dYc, dimensionless; 1 when the coordinate is
        //  the mass fraction itself and the declared value otherwise.
        scalar progressDYc_;

        //- v2: transported C is a sum of these species mass fractions.
        wordList progressSpecies_;
        scalarField progressMin_;
        scalarField progressMax_;

        //- Diagnostic-only lookup clipping, never changes transported fields.
        mutable scalar lookupCount_;
        mutable scalar clipCount_;
        mutable scalar maxProgressExcursion_;
        mutable scalar maxZExcursion_;


    // Private Member Functions

        //- Locate the cell and the weight on the upper node.  Refuses on
        //  bounds unless the policy is CLAMP_TO_BOUNDS.
        void cell
        (
            const scalarField& grid,
            const scalar value,
            const char* labelName,
            label& i,
            scalar& w
        ) const;

        //- Return the interpolated value of one flat block at (i, j, wZ, wc)
        static scalar interpolate
        (
            const scalarField& block,
            const label nC,
            const label i,
            const label j,
            const scalar wZ,
            const scalar wc
        );

        //- Refuse with a message that names the file and the defect
        void refuse(const string& reason) const;

        void validateProgressMapping() const;
        scalar mappedProgress(const label i, const scalar wZ, const scalar C) const;


public:

    // Constructors

        //- Construct from a table path; validates everything it can
        explicit fgmTableReader
        (
            const fileName& path,
            const boundsPolicy policy = ERROR_ON_BOUNDS
        );

        //- Disallow default bitwise copy construction
        fgmTableReader(const fgmTableReader&) = delete;


    //- Destructor
    ~fgmTableReader();


    // Member Functions

        //- Path of the table
        const fileName& path() const
        {
            return path_;
        }

        //- Provenance string from the header
        const string& source() const
        {
            return source_;
        }

        //- Profile digest from the header, or "none"
        const string& profileSha256() const
        {
            return profileSha256_;
        }

        //- Species names in table order
        const wordList& species() const
        {
            return species_;
        }

        //- Grid sizes
        label nZ() const
        {
            return nZ_;
        }

        label nC() const
        {
            return nC_;
        }

        //- Grids
        const scalarField& z() const
        {
            return z_;
        }

        const scalarField& c() const
        {
            return c_;
        }

        //- True when the table carries a diagnostic temperature block
        bool hasTdiag() const
        {
            return Tdiag_.size() > 0;
        }

        //- Worst |sum(Y) - 1| measured over the table nodes
        scalar worstSpeciesSum() const
        {
            return worstSpeciesSum_;
        }

        //- Progress coordinate as declared by the table
        const string& progressCoordinate() const
        {
            return progressCoordinate_;
        }

        //- Normalization width dYc; 1 for a mass-fraction coordinate
        scalar progressDYc() const
        {
            return progressDYc_;
        }

        //- True when the transported coordinate is a normalized function of
        //  the composition progress variable
        bool normalisedCoordinate() const
        {
            return progressCoordinate_ == "normalised";
        }

        bool mappedMassFraction() const
        {
            return progressCoordinate_ == "mass-fraction-mapped";
        }

        scalar lookupCount() const { return lookupCount_; }
        scalar clipCount() const { return clipCount_; }
        scalar maxProgressExcursion() const { return maxProgressExcursion_; }
        scalar maxZExcursion() const { return maxZExcursion_; }

        //- Volumetric source of the *transported* coordinate, in kg/(m3 s),
        //  from the tabulated Sc.  This is the only place the conversion is
        //  applied: Sc is the source of Yc, so a normalized coordinate takes
        //  Sc/dYc and a mass-fraction coordinate takes Sc as it stands.  No
        //  density factor, no linearisation and no clamping belong here.
        scalar sourceOfC(const scalar Sc) const
        {
            return normalisedCoordinate() ? Sc/progressDYc_ : Sc;
        }

        //- Strict v2 fixed-Z source curve and integration. No lookup clipping.
        void sourceCurve
        (
            const scalar Z, std::vector<double>& coordinates,
            std::vector<double>& sources
        ) const;

        forgeFgm::SourceAdvance advanceSource
        (
            const scalar Z, const scalar density,
            const scalar initial, const scalar duration
        ) const;

        //- Interpolate every block at (Z, c). ``Y`` is resized to the number
        //  of tabulated species and filled in table order.
        void lookup
        (
            const scalar Z,
            const scalar c,
            scalarField& Y,
            scalar& Sc,
            scalar& Q,
            scalar& Tdiag
        ) const;

        //- Write a one-line summary for logs and evidence files
        void writeSummary(Ostream& os) const;


    // Member Operators

        //- Disallow default bitwise assignment
        void operator=(const fgmTableReader&) = delete;
};


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

} // End namespace fgm
} // End namespace Foam

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#endif

// ************************************************************************* //
