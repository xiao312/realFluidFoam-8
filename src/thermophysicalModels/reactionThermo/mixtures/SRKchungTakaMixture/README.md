# SRK mixture transport setup

This module constructs the existing SRK/Chung mixture from the current cell or
patch composition. Its formulas, summation order and historical corrected X/Y
remain unchanged. It owns no cache and adds no object-layout members.

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
