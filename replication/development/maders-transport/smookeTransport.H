/*---------------------------------------------------------------------------*\
  OpenFOAM transport adapter, derived from Foundation constTransport interface.
  Copyright (C) 2011-2019 OpenFOAM Foundation (base implementation).
  Copyright (C) 2026 FlamePilot contributors (Smooke constitutive functions).
  GPL version 3 or later; without any warranty. See repository COPYING.
\*---------------------------------------------------------------------------*/
#ifndef smookeTransport_H
#define smookeTransport_H
#include "constTransport.H"
#include <cmath>

namespace Foam
{
template<class Thermo>
class smookeTransport : public constTransport<Thermo>
{
    typedef constTransport<Thermo> Base;
    explicit smookeTransport(const Base& base) : Base(base) {}
public:
    smookeTransport(const word& name, const smookeTransport& other) : Base(name, other) {}
    explicit smookeTransport(const dictionary& dict) : Base(dict) {}
    autoPtr<smookeTransport> clone() const { return autoPtr<smookeTransport>(new smookeTransport(*this)); }
    static autoPtr<smookeTransport> New(const dictionary& dict)
    {
        return autoPtr<smookeTransport>(new smookeTransport(dict));
    }
    static word typeName() { return "smooke<" + Thermo::typeName() + '>'; }
    scalar mu(const scalar p, const scalar T) const
    {
        return 1.67e-8*this->Cp(p,T)*std::pow(T/298., .51);
    }
    scalar kappa(const scalar p, const scalar T) const
    {
        return 2.58e-5*this->Cp(p,T)*std::pow(T/298., .69);
    }
    scalar alphah(const scalar p, const scalar T) const
    {
        return kappa(p,T)/this->Cp(p,T);
    }
    void operator+=(const smookeTransport& other) { Base::operator+=(other); }
    void operator*=(const scalar value) { Base::operator*=(value); }
    friend smookeTransport operator+(const smookeTransport& a, const smookeTransport& b)
    {
        return smookeTransport(static_cast<const Base&>(a)+static_cast<const Base&>(b));
    }
    friend smookeTransport operator*(const scalar s, const smookeTransport& value)
    {
        return smookeTransport(s*static_cast<const Base&>(value));
    }
    friend Ostream& operator<<(Ostream& stream, const smookeTransport& value)
    {
        value.write(stream);
        return stream;
    }
};
}
#endif
