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

Class
    Foam::CombustionModel

Description
    Combustion models for templated thermodynamics

SourceFiles
    CombustionModelI.H
    CombustionModel.C
    CombustionModelNew.C

\*---------------------------------------------------------------------------*/

#ifndef CombustionModel_H
#define CombustionModel_H

#include "combustionModel.H"
#include "autoPtr.H"
#include "runTimeSelectionTables.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

namespace Foam
{

/*---------------------------------------------------------------------------*\
                     class CombustionModel Declaration
\*---------------------------------------------------------------------------*/

template<class ReactionThermo>
class CombustionModel
:
    public combustionModel
{
public:

    //- Thermo type
    typedef ReactionThermo reactionThermo;


    //- Runtime type information
    TypeName("CombustionModel");


    //- Declare run-time constructor selection tables
    declareRunTimeSelectionTable
    (
        autoPtr,
        CombustionModel,
        dictionary,
        (
            const word& modelType,
            const ReactionThermo& thermo,
            const compressibleMomentumTransportModel& turb,
            const word& combustionProperties
        ),
        (modelType, thermo, turb, combustionProperties)
    );


    // Constructors

        //- Construct from components
        CombustionModel
        (
            const word& modelType,
            const ReactionThermo& thermo,
            const compressibleMomentumTransportModel& turb,
            const word& combustionProperties
        );


        //- Selector
        static autoPtr<CombustionModel> New
        (
            const ReactionThermo& thermo,
            const compressibleMomentumTransportModel& turb,
            const word& combustionProperties=combustionPropertiesName
        );


    //- Destructor
    virtual ~CombustionModel();


    // Member Functions

        //- Return const access to the thermo package
        virtual const ReactionThermo& thermo() const = 0;


    // IO

        //- Update properties from given dictionary
        virtual bool read();


    // Tabulated-composition interface
    //
    // These four are appended AFTER every virtual the unmodified OpenFOAM 8
    // header declares, and the order matters: the virtual table of
    // CombustionModel<ReactionThermo> is what a caller compiled against the
    // unmodified header indexes into, and the image's own reaction thermo
    // library was compiled that way.  Inserting a virtual ahead of read() would
    // silently redirect such a caller to the new slot - return false where it
    // asked for read() - instead of failing loudly.  Appending keeps slots 0..2
    // (~CombustionModel, thermo, read) exactly where they were, so a rebuilt
    // libcombustionModels can be loaded by a binary that was not rebuilt, and
    // the ABI question becomes one of the four checks the work order names
    // rather than a bet.

        //- True when the model prescribes the composition from a table, so a
        //  solver must skip the species equations instead of solving them with
        //  a zero source.  False for every reacting model.
        virtual bool compositionTabulated() const
        {
            return false;
        }

        //- True when the model transports a progress variable itself, so a
        //  solver must transport that variable and apply this model's source.
        //  False for every model that reacts the species directly.
        virtual bool transportsProgress() const
        {
            return false;
        }

        //- The transported progress variable, or nullptr when the model has
        //  none.  The solver solves this field, so it is the model's own field,
        //  not a copy and not a name looked up in the registry.
        virtual volScalarField* progressVariable()
        {
            return nullptr;
        }

        //- Volumetric source of the progress variable [kg/(m3 s)].  Undefined
        //  for models that transport no progress variable; a solver only asks
        //  when transportsProgress() is true.
        virtual tmp<volScalarField> progressSource() const;
};


// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

} // End namespace Foam

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#ifdef NoRepository
    #include "CombustionModel.C"
#endif

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#endif

// ************************************************************************* //
