#ifndef relaxedTable_H
#define relaxedTable_H
#include "ThermoCombustion.H"
#include "steadyFlameletTable.H"

namespace Foam { namespace combustionModels {
template<class ReactionThermo>
class relaxedTable : public ThermoCombustion<ReactionThermo>
{
    autoPtr<forgeSteady::Table> table_;
    volScalarField Z_, c_, temperature_, heatRelease_;
    labelList map_;
    List<scalarField> targets_;
    scalarField formationEnthalpy_;
    scalar relaxationSteps_;
    bool allowEndpointRoundoff_;
    label co2_, co_;
    void refuse(const string&) const;
public:
    TypeName("relaxedTable");
    relaxedTable(const word&, const ReactionThermo&,
        const compressibleMomentumTransportModel&, const word&);
    virtual ~relaxedTable() {}
    virtual void correct();
    virtual void correctSpeciesAfterTransport();
    virtual tmp<fvScalarMatrix> R(volScalarField&) const;
    virtual tmp<volScalarField> Qdot() const;
    virtual bool compositionTabulated() const { return false; }
    virtual bool transportsMixtureFraction() const { return true; }
    virtual bool supportsAbsoluteEnthalpy() const { return true; }
    virtual bool transportsProgress() const { return false; }
    virtual bool read();
    relaxedTable(const relaxedTable&) = delete;
    void operator=(const relaxedTable&) = delete;
};
}}
#ifdef NoRepository
#include "relaxedTable.C"
#endif
#endif
