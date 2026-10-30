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

## Prepared candidate, not built or adopted

`prepare_cold_patch.py` prepares four scalar-source changes and one small header.
It preserves ordinary-temperature arithmetic and uses signed combined logarithms
where the separate exponent exceeds magnitude 650. That threshold is numerical
headroom, not a physical model parameter. The candidate includes elementary and
third-body reactions in production and all three sensitivity variants. Existing
third-body multipliers and their derivatives remain; negative A and multiplier
signs are retained, zero factors remain exactly zero, and no material overflow is
clipped. Thermodynamic coefficients, reaction coefficients and special-order
concentration products are unchanged. Lindemann/Troe paths remain unchanged and
are explicitly outside the cold-stability claim. The unused vectorized
`flamelet_rhs_test1` is also outside the supported candidate path.

A broader future implementation could retain a signed logarithmic magnitude of the complete elementary Arrhenius rate,
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

## Bounded qualification sequence

1. Execute the eight-state original-runtime probe and confirm which compiled
   evaluator and species fail. Preserve the original receipt.
2. Build a new isolated runtime with the already qualified energy patch and this
   candidate. Record both patch manifests, all changed-file hashes, and the actual
   extension hash. Do not identify it using only the old energy-patch receipt.
3. Repeat the eight-state probe. Require finite full/isolated rates and compare the
   reaction-229 coefficient with its combined-log expression, not Cantera's
   underflowed coefficient.
4. At a few declared cold and ordinary-temperature states, check the actual dense
   and sparse Jacobians against perturbations of the actual production kernel.
   Include temperature, density and the affected H/CN/HCN composition directions.
   The no-TBAF option retains its declared approximation; do not require omitted
   third-body derivatives to match exact finite differences.
5. Run an independently fresh cold 85/288 K trajectory with the steady control
   explicitly disabled. Preserve the constant-Cp thermal extension versus NASA
   chemistry extrapolation distinction. Inspect conservation, clipping and branch
   coverage before producing any new G2 table.

Candidate generation, `git apply --check`, and Python syntax checks can run without
modifying upstream. Compilation, kernel qualification and physical trajectories
remain allocated work and are not claimed by the candidate generator.

Primary source:
[pinned Griffon chemistry kernel](https://github.com/sandialabs/Spitfire/blob/735711dc4a426cc7504747d732f2e7fcc3db2c23/src/spitfire/griffon/src/chemistry_kernels.cpp).
