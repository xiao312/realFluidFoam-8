# SRK mixture transport setup

This module constructs the existing SRK/Chung mixture from the current cell or
patch composition. Its formulas, nonzero summation order and historical corrected
X/Y remain unchanged. It owns no cache and adds no object-layout members.

The explicit `fgmSkipUnusedDimix yes` policy may omit only preparation of unused
Takahashi mass-diffusion matrices. It requires hePsiThermo, immutable controls,
absolute Ha, laminar Fourier transport, and named fgmTable or steadyFlamelet
composition. Validation runs in this mixture constructor before heThermo's first
enthalpy query. Queries subsequently inspect only the existing in-memory flag.
Rereading while enabled is refused; use a fresh process and time-zero case.

The optimized branch retains all EOS reductions, all eight Chung scalars and
corrected X/Y, then calls `updateTRANSWithoutDiffusion`. It skips TCMD/PCMD
allocation and construction; that transport method clears all four diffusion
matrices so raw Dimix access fails explicitly instead of reading stale values.
The switch-off path retains its original arithmetic and complete diffusion.

With the same explicit policy enabled, pair reductions also omit terms whose
uncorrected mole-fraction operand is exactly zero. There is no small-species
threshold, removal or renormalization. All nonzero terms retain their original
order. This is useful in cold pure-stream cells, where the dense pair loop
otherwise performs thousands of zero additions. The constructor checks that
all omitted pair coefficients are finite, so this path cannot conceal an invalid
coefficient through a skipped zero multiplication. The later historical 1e-40
correction to transport X/Y remains unchanged. No new configuration is added.

This optimization requires a new allocated build and exact comparison against
the preceding runtime. Include pure and mixed cell/patch properties, alternating
compositions, the existing physical interior cases and a matched fresh cold run.
Record wall-time separately from field agreement. Until those comparisons pass,
this revision is an unqualified performance candidate.

Dependencies are basicSpecieMixture, the shared fgmDimixPolicy in basic thermo,
and Chung/Takahashi transport. Dependent template registrations are the basic
and reaction thermophysical libraries; rebuild both and the diagnostic probe.
No secrets, network access, scheduler calls or persistent cache are involved.

Minimal configuration adds `fgmSkipUnusedDimix yes;` to an otherwise qualified
hePsiThermo/SRK, absolute-Ha, laminar/Fourier table-composition case. The complete
policy is documented in `basic/psiThermo/README.fgm-diffusion.md`.

Verification: `git diff --check`, then allocated six-state property/inversion
comparisons (cell and patch, alternating compositions), raw-Dimix and policy
refusal controls, and fresh physical 48-cell FGM/steady-flamelet off/on pairs.
Unchanged arithmetic requires exactly equal rho/Cp/Cv/h/mu/alpha/inversion and
written fields/budgets. A successful build alone is not qualification.
