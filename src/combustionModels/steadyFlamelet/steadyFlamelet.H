#ifndef steadyFlamelet_H
#define steadyFlamelet_H
#include "ThermoCombustion.H"
#include "steadyFlameletTable.H"

namespace Foam { namespace combustionModels {
template<class ReactionThermo>
class steadyFlamelet : public ThermoCombustion<ReactionThermo>
{
    autoPtr<forgeSteady::Table> table_;
    volScalarField Z_, c_, temperature_, heatRelease_;
    labelList map_;
    label co2_, co_;
    void refuse(const string&) const;
public:
    TypeName("steadyFlamelet");
    steadyFlamelet(const word&, const ReactionThermo&,
        const compressibleMomentumTransportModel&, const word&);
    virtual ~steadyFlamelet() {}
    virtual void correct();
    virtual tmp<fvScalarMatrix> R(volScalarField&) const;
    virtual tmp<volScalarField> Qdot() const;
    virtual bool compositionTabulated() const { return true; }
    virtual bool transportsProgress() const { return false; }
    virtual bool read();
    steadyFlamelet(const steadyFlamelet&) = delete;
    void operator=(const steadyFlamelet&) = delete;
};
}}
#ifdef NoRepository
#include "steadyFlamelet.C"
#endif
#endif
