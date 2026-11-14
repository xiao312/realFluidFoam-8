# Parallel Schmitt and G2 baseline, 14 November 2026

The owner requested one campaign for Schmitt Figures5/6, Sharma Figure4b,
Cavalieri Figure6 and Schmitt Figure21. Preserve the Maders work and its failures.
This batch starts new cases at time zero. It does not continue evolved fields.

The contact branch runs six published initial interfaces with our pressure-based
solver and full SRK/Chung library. It does not implement AVBP artificial viscosity.
Its new preparation module is `validation/schmitt-contact`.

Two G2 condition branches are needed:5.61MPa/85K O2/288K CH4 for Sharma/Cavalieri,
and5.6MPa/83K O2/300K CH4 for Schmitt. Preserve paper-specific sampling and velocity
normalization. Both consume actual mass-flow/mesh-area audits, not ideal-gas inlet
velocity placeholders. Sharma's prose swaps fuel/oxygen mass flows; the retained
Müller/Singla/Cavalieri convention is O2=44.4g/s and CH4=143.1g/s.

The available baseline has a paper-exit10000-cell wedge, SRK, unity-Le transport
and a fixed-chi steady-flamelet/delta-PDF closure. RANS is an explicit diagnostic,
not a replacement claim for the papers' three-dimensional LES/PDF models.
The retained200622-cell wedge remains a separate geometry asset. Its oxygen inlet
radius and axial origin differ; it must not be silently relabeled as a paper mesh.
Source and field/energy controls must run before each longer case is admitted.
Approximate-manifold residual failures remain failed while transport experiments
proceed independently. A failure must produce data and an actionable diagnosis.

Each G2 first-round allocation is bounded to24hours. The physical target includes
initial development and a subsequent50–60ms observation window, when reached.
Saved early profiles remain transient. A time window cannot be labeled a paper
mean until it has actually been sampled. Sharma's50flow-through-time preparation
is a separate unmet condition unless measured. No completion or acceptance is
inferred from queue admission or running allocations.

The operator owns scheduler receipts, immutable input/output hashes, sampled
profiles and the local Forge comparison import. Keep bulky fields/logs on SCNet.
New code/result commits and scientific acceptance remain separate. The next
development cycle changes one identified solver/case component, regenerates
fresh cases, and compares against this retained baseline at matched times.
