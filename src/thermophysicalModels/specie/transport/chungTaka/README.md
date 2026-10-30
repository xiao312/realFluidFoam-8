# Chung transport and Takahashi diffusion data

This transport template evaluates the existing Chung viscosity/conductivity and
Takahashi mixture diffusivity. Default construction/update behavior is unchanged.

The public `updateTRANSWithoutDiffusion` method accepts the same eight Chung
scalars and corrected Y/X as `updateTRANS`, but explicitly clears its four
diffusion matrices. It is used only by the guarded SRK mixture optimization;
mu/kappa still receive X because their implementation uses its sum. Raw Dimix
rejects absent or inconsistent matrix dimensions before any indexing. It does
not return zero, extrapolate or consume stale diffusion data.

No class members, layout, virtual methods or cache are added. Inputs and outputs
are in-memory scientific values. There are no filesystem/credential or network
operations. Dependents are thermophysical template-registration libraries and
the SRK mixture; their owning binaries and diagnostic probe must be rebuilt.

Verification uses actual cold O2/CH4 and hot/cold physical mixture properties,
inversions and fresh CFD comparisons. One direct raw-Dimix call after the light
update must fail; a complete update must retain valid diffusivity. See the SRK
mixture README and the physical qualification packet. No scientific acceptance
is implied by introducing this interface.
