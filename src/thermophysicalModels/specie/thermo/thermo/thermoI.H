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

\*---------------------------------------------------------------------------*/

#include "thermo.H"
#include "IOmanip.H"
#include <cmath>

// * * * * * * * * * * * * * Private Member Functions  * * * * * * * * * * * //

template<class Thermo, template<class> class Type>
inline Foam::species::thermo<Thermo, Type>::thermo
(
    const Thermo& sp
)
:
    Thermo(sp)
{}


template<class Thermo, template<class> class Type>
inline Foam::scalar Foam::species::thermo<Thermo, Type>::T
(
    const scalar f,
    const scalar p,
    const scalar T0,
    scalar (thermo<Thermo, Type>::*F)(const scalar, const scalar) const,
    scalar (thermo<Thermo, Type>::*dFdT)(const scalar, const scalar)
        const,
    scalar (thermo<Thermo, Type>::*limit)(const scalar) const,
    const bool diagnostics
) const
{
    if (T0 < 0)
    {
        FatalErrorInFunction
            << "Negative initial temperature T0: " << T0
            << abort(FatalError);
    }

    const auto valueAt = [&](const scalar temperature)
    {
        return (this->*F)(p, temperature);
    };
    const auto tolerance = [&](const scalar value)
    {
        return scalar(1e-8) + scalar(1e-10)*max
        (
            scalar(1), max(mag(f), mag(value))
        );
    };
    scalar temperature = (this->*limit)(T0);
    scalar value = valueAt(temperature);
    scalar residual = value-f;
    scalar bestTemperature = temperature;
    scalar bestResidual = std::isfinite(residual) ? mag(residual) : GREAT;
    const auto remember = [&](const scalar trial, const scalar error)
    {
        if (std::isfinite(error) && mag(error)<bestResidual)
        {
            bestTemperature=trial;
            bestResidual=mag(error);
        }
    };

    // Require an energy residual, not just a small temperature update.
    for (int iteration=0; iteration<maxIter_; ++iteration)
    {
        if (std::isfinite(value) && mag(residual)<=tolerance(value))
            return temperature;
        const scalar derivative=(this->*dFdT)(p,temperature);
        if (!std::isfinite(derivative) || derivative==0
         || !std::isfinite(residual)) break;
        const scalar step=-residual/derivative;
        bool improved=false;
        scalar fraction=1;
        for (int search=0; search<8; ++search)
        {
            const scalar raw=temperature+fraction*step;
            if (std::isfinite(raw) && raw>0)
            {
                const scalar trial=(this->*limit)(raw);
                const scalar trialValue=valueAt(trial);
                const scalar trialResidual=trialValue-f;
                remember(trial,trialResidual);
                if (std::isfinite(trialValue)
                 && mag(trialResidual)<mag(residual))
                {
                    temperature=trial;
                    value=trialValue;
                    residual=trialResidual;
                    improved=true;
                    break;
                }
            }
            fraction*=0.5;
        }
        if (!improved) break;
    }

    // Bracket only after Newton stalls. Respect the model's temperature limits.
    scalar lower=(this->*limit)(max(scalar(1),min(T0,temperature)*0.5));
    scalar upper=(this->*limit)(max(scalar(4000),max(T0,temperature)*2));
    scalar lowerValue=valueAt(lower), upperValue=valueAt(upper);
    scalar lowerResidual=lowerValue-f, upperResidual=upperValue-f;
    const auto oppositeSigns = [](const scalar left, const scalar right)
    {
        return (left<0 && right>0) || (left>0 && right<0);
    };
    for (int expansion=0; expansion<20; ++expansion)
    {
        remember(lower,lowerResidual);
        remember(upper,upperResidual);
        if (std::isfinite(lowerValue) && mag(lowerResidual)<=tolerance(lowerValue))
            return lower;
        if (std::isfinite(upperValue) && mag(upperResidual)<=tolerance(upperValue))
            return upper;
        if (std::isfinite(lowerResidual) && std::isfinite(upperResidual)
         && oppositeSigns(lowerResidual,upperResidual)) break;
        const scalar nextLower=(this->*limit)(max(scalar(1),lower*0.5));
        const scalar nextUpper=(this->*limit)(upper*2);
        if (nextLower==lower && nextUpper==upper) break;
        lower=nextLower; upper=nextUpper;
        lowerValue=valueAt(lower); upperValue=valueAt(upper);
        lowerResidual=lowerValue-f; upperResidual=upperValue-f;
    }
    if (std::isfinite(lowerResidual) && std::isfinite(upperResidual)
     && oppositeSigns(lowerResidual,upperResidual))
    {
        for (int iteration=0; iteration<maxIter_; ++iteration)
        {
            const scalar middle=lower+(upper-lower)*0.5;
            if (middle==lower || middle==upper) break;
            const scalar middleValue=valueAt(middle);
            const scalar middleResidual=middleValue-f;
            remember(middle,middleResidual);
            if (!std::isfinite(middleValue)) break;
            if (mag(middleResidual)<=tolerance(middleValue)) return middle;
            if (oppositeSigns(lowerResidual,middleResidual))
            {
                upper=middle; upperResidual=middleResidual;
            }
            else
            {
                lower=middle; lowerResidual=middleResidual;
            }
        }
    }
    FatalErrorInFunction
        << "Thermodynamic energy inversion did not converge: p=" << p
        << " target=" << f << " T0=" << T0
        << " bestT=" << bestTemperature << " bestAbsResidual=" << bestResidual
        << ". No unconverged temperature accepted."
        << exit(FatalError);
    return bestTemperature; // Unreachable; the error exits or throws.

}


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

template<class Thermo, template<class> class Type>
inline Foam::species::thermo<Thermo, Type>::thermo
(
    const word& name,
    const thermo& st
)
:
    Thermo(name, st)
{}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

template<class Thermo, template<class> class Type>
inline Foam::word
Foam::species::thermo<Thermo, Type>::heName()
{
    return Type<thermo<Thermo, Type>>::energyName();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::Cpv(const scalar p, const scalar T) const
{
    return Type<thermo<Thermo, Type>>::Cpv(*this, p, T);
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::gamma(const scalar p, const scalar T) const
{
    const scalar Cp = this->Cp(p, T);
    return Cp/(Cp - this->CpMCv(p, T));
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::CpByCpv
(
    const scalar p,
    const scalar T
) const
{
    return Type<thermo<Thermo, Type>>::CpByCpv(*this, p, T);
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::HE(const scalar p, const scalar T) const
{
    return Type<thermo<Thermo, Type>>::HE(*this, p, T);
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::G(const scalar p, const scalar T) const
{
    return this->Ha(p, T) - T*this->S(p, T);
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::A(const scalar p, const scalar T) const
{
    return this->Ea(p, T) - T*this->S(p, T);
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::cp(const scalar p, const scalar T) const
{
    return this->Cp(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::ha(const scalar p, const scalar T) const
{
    return this->Ha(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::hs(const scalar p, const scalar T) const
{
    return this->Hs(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::hc() const
{
    return this->Hf()*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::s(const scalar p, const scalar T) const
{
    return this->S(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::he(const scalar p, const scalar T) const
{
    return this->HE(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::cv(const scalar p, const scalar T) const
{
    return this->Cv(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::es(const scalar p, const scalar T) const
{
    return this->Es(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::ea(const scalar p, const scalar T) const
{
    return this->Ea(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::g(const scalar p, const scalar T) const
{
    return this->G(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::a(const scalar p, const scalar T) const
{
    return this->A(p, T)*this->W();
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::K(const scalar p, const scalar T) const
{
    scalar arg = -this->Y()*this->Gstd(T)/(RR*T);

    if (arg < 600)
    {
        return exp(arg);
    }
    else
    {
        return rootVGreat;
    }
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::Kp(const scalar p, const scalar T) const
{
    return K(p, T);
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::Kc(const scalar p, const scalar T) const
{
    const scalar nm = this->Y()/this->W();

    if (equal(nm, small))
    {
        return Kp(p, T);
    }
    else
    {
        return Kp(p, T)*pow(Pstd/(RR*T), nm);
    }
}


template<class Thermo, template<class> class Type>
inline Foam::scalar Foam::species::thermo<Thermo, Type>::Kx
(
    const scalar p,
    const scalar T
) const
{
    const scalar nm = this->Y()/this->W();

    if (equal(nm, small))
    {
        return Kp(p, T);
    }
    else
    {
        return Kp(p, T)*pow(Pstd/p, nm);
    }
}


template<class Thermo, template<class> class Type>
inline Foam::scalar Foam::species::thermo<Thermo, Type>::Kn
(
    const scalar p,
    const scalar T,
    const scalar n
) const
{
    const scalar nm = this->Y()/this->W();

    if (equal(nm, small))
    {
        return Kp(p, T);
    }
    else
    {
        return Kp(p, T)*pow(n*Pstd/p, nm);
    }
}


template<class Thermo, template<class> class Type>
inline Foam::scalar Foam::species::thermo<Thermo, Type>::THE
(
    const scalar he,
    const scalar p,
    const scalar T0
) const
{
    return Type<thermo<Thermo, Type>>::THE(*this, he, p, T0);
}


template<class Thermo, template<class> class Type>
inline Foam::scalar Foam::species::thermo<Thermo, Type>::THs
(
    const scalar hs,
    const scalar p,
    const scalar T0
) const
{
    return T
    (
        hs,
        p,
        T0,
        &thermo<Thermo, Type>::Hs,
        // &thermo<Thermo, Type>::Cp, // This is only for ideal gas
        &thermo<Thermo, Type>::dHsdT, // for real gas, Nam 
        &thermo<Thermo, Type>::limit
    );
}


template<class Thermo, template<class> class Type>
inline Foam::scalar Foam::species::thermo<Thermo, Type>::THa
(
    const scalar ha,
    const scalar p,
    const scalar T0
) const
{
    return T
    (
        ha,
        p,
        T0,
        &thermo<Thermo, Type>::Ha,
        &thermo<Thermo, Type>::Cp,
        &thermo<Thermo, Type>::limit
    );
}


template<class Thermo, template<class> class Type>
inline Foam::scalar Foam::species::thermo<Thermo, Type>::TEs
(
    const scalar es,
    const scalar p,
    const scalar T0
) const
{
    return T
    (
        es,
        p,
        T0,
        &thermo<Thermo, Type>::Es,
        &thermo<Thermo, Type>::Cv,
        &thermo<Thermo, Type>::limit
    );
}


template<class Thermo, template<class> class Type>
inline Foam::scalar Foam::species::thermo<Thermo, Type>::TEa
(
    const scalar ea,
    const scalar p,
    const scalar T0
) const
{
    return T
    (
        ea,
        p,
        T0,
        &thermo<Thermo, Type>::Ea,
        &thermo<Thermo, Type>::Cv,
        &thermo<Thermo, Type>::limit
    );
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::dKcdTbyKc
(
    const scalar p,
    const scalar T
) const
{
    const scalar dKcdTbyKc =
        (this->S(Pstd, T) + this->Gstd(T)/T)*this->Y()/(RR*T);

    const scalar nm = this->Y()/this->W();
    if (equal(nm, small))
    {
        return dKcdTbyKc;
    }
    else
    {
        return dKcdTbyKc - nm/T;
    }
}


template<class Thermo, template<class> class Type>
inline Foam::scalar
Foam::species::thermo<Thermo, Type>::dcpdT(const scalar p, const scalar T) const
{
    return this->dCpdT(p, T)*this->W();;
}


// * * * * * * * * * * * * * * * Member Operators  * * * * * * * * * * * * * //

template<class Thermo, template<class> class Type>
inline void Foam::species::thermo<Thermo, Type>::operator+=
(
    const thermo<Thermo, Type>& st
)
{
    Thermo::operator+=(st);
}


template<class Thermo, template<class> class Type>
inline void Foam::species::thermo<Thermo, Type>::operator*=(const scalar s)
{
    Thermo::operator*=(s);
}


// * * * * * * * * * * * * * * * Friend Operators  * * * * * * * * * * * * * //

template<class Thermo, template<class> class Type>
inline Foam::species::thermo<Thermo, Type> Foam::species::operator+
(
    const thermo<Thermo, Type>& st1,
    const thermo<Thermo, Type>& st2
)
{
    return thermo<Thermo, Type>
    (
        static_cast<const Thermo&>(st1) + static_cast<const Thermo&>(st2)
    );
}


template<class Thermo, template<class> class Type>
inline Foam::species::thermo<Thermo, Type> Foam::species::operator*
(
    const scalar s,
    const thermo<Thermo, Type>& st
)
{
    return thermo<Thermo, Type>
    (
        s*static_cast<const Thermo&>(st)
    );
}


template<class Thermo, template<class> class Type>
inline Foam::species::thermo<Thermo, Type> Foam::species::operator==
(
    const thermo<Thermo, Type>& st1,
    const thermo<Thermo, Type>& st2
)
{
    return thermo<Thermo, Type>
    (
        static_cast<const Thermo&>(st1) == static_cast<const Thermo&>(st2)
    );
}


// ************************************************************************* //
