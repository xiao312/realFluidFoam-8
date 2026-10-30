# Cold reaction-rate arithmetic under investigation

The 85 K diagnostic export returned a nonfinite chemistry comparison. The raw
temperature and composition were retained. Cantera 3.2.0 evaluations at pure O2
85 K, CH4 288 K, and O2 300 K have finite species/reaction rates; that observation
does not identify the failing Griffon path by itself.

In pinned Spitfire 735711dc, `chemistry_kernels.cpp` first evaluates the forward
Arrhenius coefficient, then multiplies it by an exponential inverse equilibrium
constant. Products of species concentrations are applied afterward. The public
API exposes species production, so `cold_rate_probe.py` evaluates both the full
mechanism and the original reaction 229 in isolation to test this suspected path.
No mechanism is substituted in a physical run.

For GRI reaction 229, HCN + M <=> CN + H + M, at 85 K:

- log(kf) = -704.2554094 when the complete Arrhenius expression is combined.
- log(1/Kc) = 733.4544973.
- log(kr) = 29.1990879 before the third-body concentration factor.
- The separate Arrhenius exponential underflows before multiplication by A,
  and exp(log(1/Kc)) overflows. Their product can become 0 times infinity.

Cantera's zero reverse rate constant at this state is also affected by the
forward-coefficient underflow. The finite zero net rate in the unmixed stream
is not sufficient evidence that its individual reverse coefficient is accurate.
The combined logarithm gives approximately 4.79736e12 before the third-body factor,
but the required product concentrations are zero at the probe's pure inlet.

## Candidate repair strategy, not implemented

Retain a signed logarithmic magnitude of the complete elementary Arrhenius rate,
including temperature and activation-energy terms before exponentiation. Form the
reverse logarithm by adding the thermodynamic inverse-equilibrium term. Form rate
of progress by adding concentration logarithms, with exact zero-concentration
branches handled before exponentiation. This avoids creating infinity before
multiplication by a physically zero concentration.

A general correction must also preserve negative pre-exponential factors where
allowed, irreversible/special-order semantics, third-body efficiencies, Lindemann
and Troe falloff, and the associated derivative kernels. A blanket log(k), an
exponent cap, or replacing nonfinite values with zero would not meet that contract.
Falloff needs stable reduced-pressure and broadening calculations; preserving only
the final underflowed coefficient loses information. Prefer a narrowly verified
elementary/three-body correction first if the actual compiled probe confirms it.
Compare finite-temperature chemistry and derivatives at retained physical states
before using any change in a cold flame. Keep this separate from the eight-site
energy-index correction and its fresh warm 129/257 comparisons.

Primary source:
[pinned Griffon chemistry kernel](https://github.com/sandialabs/Spitfire/blob/735711dc4a426cc7504747d732f2e7fcc3db2c23/src/spitfire/griffon/src/chemistry_kernels.cpp).
