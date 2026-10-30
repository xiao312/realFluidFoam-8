# Fixed-dissipation steady-flamelet diagnostic

`steadyFlamelet` maps transported mixture fraction Z to composition on one
retained physical burning flamelet. It is a separate laminar, delta-PDF,
fixed-dissipation diagnostic; it is not the FGM progress-variable closure and
does not qualify a turbulent presumed-PDF or LES model. Retained profiles which
failed their steady criterion remain labelled approximate steady in provenance.

The table supplies all species, diagnostic temperature and formation-enthalpy
heat release. The solver transports Z and absolute total enthalpy Ha. Full SRK
thermodynamics owns density and temperature by inversion. Tabulated temperature
is not assigned during the solve, and no chemical Q is added to Ha. This is an
explicit difference from a paper closure which looks up temperature directly.
The derived field c=Y_CO2+Y_CO is a diagnostic, never a transported coordinate.

Inputs: a strict v1 text table, `steadyFlameletCoeffs` with an absolute table
path, declared `fixedChi` and `chiDefinition`, Z, and a complete matching thermo
species set. Controls require absoluteEnthalpy, explicit source mode, disabled
progress source and immutable case dictionaries. Use laminar momentum and
Fourier/unity-Lewis transport. An explicit unused-Dimix switch uses the same
constructor-validated hePsi/absolute-Ha/laminar/Fourier policy as fgmTable; the
steady model has no bypass. This named-model extension requires its own actual
property and fresh CFD parity receipts before adoption. The default remains off.

Outputs: mapped Y, c, steadyTdiag, steadyQdot and lookup diagnostics. Source and
Q values are not used in transport equations. Z outside [0,1], nonfinite data,
negative species, missing/duplicate species, bad pure-stream endpoints or
species/element imbalance fail explicitly. There is no clipping or renormalizing.

The file grammar is whitespace-delimited, with no comments:

```
FORGE_STEADY_FLAMELET 1
pressure-pa 5610000
chi-definition maximum
chi-value-s-1 10000
oxidizer-temperature-k 85
fuel-temperature-k 288
species N name_1 ... name_N
elements E element_1 ... element_E
element-mass-coefficients E_times_N_values_in_element_major_order
points M
data
Z_0 T_0 Qformation298_0 Y_0_1 ... Y_0_N
...
Z_last T_last Qformation298_last Y_last_1 ... Y_last_N
end
```

N/E/M are integer counts. Z is strictly increasing with exact endpoints 0/1;
these endpoints are pure O2/CH4 at the declared temperatures. An element mass
coefficient is atomic weight times species atom count divided by species
molecular weight. Each column sums to one. Every species sum and elemental mass
fraction versus linear endpoint mixing must agree within 1e-8. Linear Z
interpolation preserves those constraints. Pressure and chi definitions/values
are retained, never inferred from a filename. Chi may be `maximum` or
`stoichiometric`; they are not interchangeable.

Dependencies: OF8 ThermoCombustion and standard C++ file parsing. The solver
refreshes Y after solving Z and before the Ha equation. It skips cEqn when
`transportsProgress()` is false; the original FGM path retains its existing
source integration and failures. All files are ordinary case inputs, with no
secrets or network operations. Downloaded paper/data provenance stays outside
source Git. The exporter, case generator, initializer and immutable run receipt
bind exact source, table, mesh and thermodynamic identities.

Minimal dictionary:

```
combustionModel steadyFlamelet;
steadyFlameletCoeffs
{
    table "/workspace/case/constant/steady.tbl";
    fixedChi 10000;
    chiDefinition maximum;
}
```

Verification: `git diff --check`, exact physical table parsing plus a focused
out-of-domain refusal, then an allocated full-SRK build and fresh small
transport/enthalpy case. Check the model sees transported Z, composition is
updated before E, c has no equation/source, Ha has no added Q and initial Y/T/p
produce Ha with the executing runtime. Compilation is not physical validation.

Cyclic boundary audits use the same weighted owner/neighbour composition as
OpenFOAM8 `coupledFvPatchField::evaluate`; nonlinear lookup of the averaged Z
is not an equivalent operation. Processor patches store their received neighbour
values and retain direct lookup checks. Physical fixed/gradient boundaries retain
their declared values and direct lookup check. This diagnostic distinction changes
no transported field or source. See the upstream OpenFOAM8 coupled and processor
patch-field implementations for their separate storage semantics.

## Explicit endpoint representation policy

The default `lookupRoundoffPolicy strict` rejects every out-of-range Z. The
opt-in `endpoint64epsilon` policy permits only an absolute lookup-coordinate
excursion at most `64*std::numeric_limits<double>::epsilon()` (about1.42e-14).
It maps that local interpolation coordinate to0 or1; it never changes the
transported Z field, equation, source or table. Material excursions and nonfinite
values still fail. This fixed bound is not a user-adjustable tolerance.

Before any lookup, each correction records the complete global cell/patch Z
range, nonfinite count and maximum outside excursion at17-digit precision.
Each correction also records global counts of mapped cell/patch lookup calls, maximum
coordinate change, and maximum endpoint elemental-mass-fraction change implied
by that coordinate mapping. Cyclic owner/neighbour calls are counted separately
as patch lookup calls. Counts describe the current correction, not unique mesh
points or a cumulative event count. Full-precision refusal messages include raw
Z, signed outside delta, fixed limit and cell/patch location.

The candidate requires a fresh strict first-step reproduction before enabling
this policy on the same inputs. The measured global excursion must fit the fixed
bound. Independent material-overshoot controls must still fail, and an interior
physical run must agree with strict mode. A successful diagnostic is not a
general bounded-transport proof or paper validation. The standalone
`endpoint-probe.C` verifies strict defaults, exact endpoint identity, unchanged
input values, full-table elemental perturbation and material refusal using the
actual retained table. Compile and run it in the same Slurm allocation.
