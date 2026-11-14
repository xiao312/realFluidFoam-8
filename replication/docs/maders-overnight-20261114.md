# Maders overnight development —14November2026,02:45Shanghai

Ignition kernel extent changed the startup, but did not resolve the persistent
inward radial-profile mismatch. The next controlled experiment halves axial
spacing while preserving radial mesh,physics and the original timezero startup.

Both full cases sustained burning for250–294ms after one ignition. At collection,
R17/127943044 had t1.194s,Tmax2096.66K,Qdiag4.190W; R18/127943180 had t1.152s,
Tmax2081.27K,Qdiag2.874W. R18 later stopped normally at1.172235s after15913s wall,
exit0:0,stillburning. This ends its matched-ignition-control role; it is neither
an extinction nor a scientifically accepted steady result. R17 continues.

| Latest saved case | Time,s | T RMS H10/H40,K | CO RMS H10/H40 |
|---|---:|---|---|
|R17 broad kernel|1.190013|369.88 /709.88|.011313 /.022274|
|R18 moderate kernel|1.150000|359.35 /793.34|.010607 /.021476|

At matched1.150s the two cases differ by10.12/61.65K RMS and29.06/161.74K maximum
at H10/H40. These differences are much smaller than their paper errors. Thus
another ignition-width fit is not the supported next action. Both remain strongly
transient;50ms maximum T changes were94/440K for R17 and755/1354K for R18. The
original1.769565s temporalminimum and thresholds remain. No steady improvement is
claimed from the earlier,closer70ms snapshot.

An independent bilinear reconstruction from the exact executed201x201 table,
using sampled Z/C and row-dependent mapped progress,agrees with solved temperature
within0.27–0.46K RMS in T>500K regions (maximum1.68K). This is separate from the
known stale-boundary fgmTdiag line field,which is excluded. Point interpolation
is not exact cell-state reconstruction. This check makes a large instantaneous
energy/table-temperature mismatch unlikely at these planes; it does not qualify
all thermodynamic dynamics or change absolute-Ha ownership.

At H40,the stoichiometric contour Z=.124236 lies at5.35/5.92mm in R17/R18,with
T peaks4.86/5.41mm versus the digitized paper peak9.695mm. These are different
physical quantities; the paper peak is not asserted to be its exact Zst contour.
The inward contour and the close table-temperature reconstruction motivate a
mixing/momentum/grid investigation instead of temperature fitting.

Source audit confirms the current Z and C equations both use the selected
thermophysical transport divj. OF8's official Fourier implementation uses the
same thermal-diffusivity coefficient in divj and divq,consistent with the declared
unity-Le model: [OF8 Fourier source](https://cpp.openfoam.org/v8/Fourier_8C_source.html).
The retained Maders text explicitly includes buoyancy,DRM19 and unity-Le/Smooke;
there is no basis here to remove buoyancy or arbitrarily rescale diffusivity.
The unresolved axial resolution is200micrometres,coarser than30–60micrometre
literature guidance. The new100micrometre control is still a partial refinement,
not a claim of author-grid replication or grid independence.

`--axial-cells` is implemented by source6cb1bb9c9254930f33bc1477912bd35f557808d9.
Positive1000-cell plans and full local case generation gave240000 total cells;
nonintegral counts failed. Actual blockMesh/checkMesh and ignition qualification
remain allocation work. Default protocols retain their previous mesh counts.

New Slurm127961776,keymaders-axial100-r1-6cb1bb9,admitted02:43:16,32ranks/64GiB,
32400s (within11:59deadline). It uses the same compiled solverea2a404/bin31b6739,
physical table35a6,and moderate kernelZ=.04–.30 as coarse R18. Read `ea2a404` as
the exact solver prefix; no new solver build is made for a mesh-only experiment.
A fresh.01s-ignition/.015s-end refined-grid startup check precedes a SEPARATE fresh
full case with.9s ignition/end2s. This short check is numerical integrity only,
not sustained survival or scientific acceptance. Environment staging is verified;
actual refined CFD is pending at this report. All compute uses adapter0d2a63b,
OF8profilef46;allstatesstart0,never reuse evolved CFD fields.

The local gallery contains updated R17/R18 comparisons and complete saved
histories,all11 views/71targets/12papers/captions retained. Both PNGs inspected;
HTTP/content hashes and history/plot metrics agree. R18 terminal reason is explicit.
Prior baseline/extinction/strict failures remain. No independent scientific
approval or publication is inferred. Operator records bind raw archive hashes,
matched-time analysis,flow/table reconstruction,run receipts and known limitations.

## 11:05 checkpoint: both full controls stopped, mismatch remains

The preceding “pending” statements describe the 02:43 launch, not current status.
The refined mesh actually passed blockMesh/checkMesh with 240000 cells and its
separate fresh-start ignition check. The full case then started from cold time0
at 02:56:21 Shanghai. No evolved fields were reused.

| Run / Slurm JobID | Final solver time | Allocation elapsed | Outcome |
| --- | ---: | ---: | --- |
| Broad coarse R17 / 127943044 | 2 s | 38496 s | Completed, exit0:0; unsteady |
| Moderate coarse R18 / 127943180 | 1.172235342 s | 15913 s | Graceful control stop, exit0:0 |
| Moderate refined R19 / 127961776 | 1.116164738 s | 30032 s | Graceful operational stop, exit0:0 |

These three allocations each used32 ranks and64GiB, totaling750.587 allocated
core-hours. This subtotal excludes earlier qualification/debugging jobs; their
usage remains recorded. The refined stop was requested at11:03:01, before its
payload timeout, and Slurm completed at11:03:51. It was not a convergence stop.
Solver exit0 and final reconstruction were verified. Its final internal diagnostic
heat release was3.91590W; the absolute-enthalpy inversion maximum relative residual
was5.47e-16. Neither measurement establishes radial-profile accuracy or complete
global energy conservation.

The latest saved refined profiles at1.11500646592s give temperature RMS errors
336.50/691.75K and CO mass-fraction RMS0.010178/0.020599 atH10/H40. Peak temperatures
are2002/2029K, but radial peaks and cold-side gradients lie too far inward. Maximum
profile changes over the final50ms are7.22/427.13K; over100ms they are55.36/1623.19K.
The lower plane is becoming quieter, while the upper plane remains transient.
The case stopped below its declared1.769565s observation minimum. The broad case
reached2s, yet still had temperature RMS348.54/689.80K and failed temporal settling.

At matched1.115s, moderate coarse/refined temperature RMS errors are287/337K atH10
and429/692K atH40. Earlier matched snapshots changed the apparent direction of
improvement. The experiment therefore demonstrates sensitivity to axial resolution
and transient phase, not grid independence or a consistent accuracy improvement.
The100micrometre axial mesh still does not reproduce the author's30–60micrometre
guidance. Do not select favorable transient frames as the paper comparison.

A read-only solved-field diagnostic estimates stoichiometric scalar dissipation
using chi=2D|gradZ|^2 and the existing Smooke unity-Le relation
D=2.58e-5*(T/298)^0.69/rho. Radial finite differences plus interpolation between five
axial lines give3.326/0.918s^-1 atH10/H40 for R17 at2s, and3.300/0.880s^-1 for R19
at1.094994s. These sampled locations fall within the table's steady0.03–60s^-1
range. This is an approximate sampled-field calculation, not the exact finite-volume
operator or evidence for coverage everywhere. It provides no support for a missing
strain-range explanation at those locations. Unqualified fgmTdiag/fgmQdot point
samples were excluded.

The physical table SHA256 remains35a6b46b5a56d2831a598acb7810119b6bc27ced27d90d217d2258514295c1cc.
The compiled solver remains ea2a4046ab239ae4fdb1197cd65fd83ebc933785, executable
31b6739c6fa57f9da4d05f8d2e4edf64cd04fe4324176ab9b8dc6ee66d850a78. The refined
case recipe remains6cb1bb9c9254930f33bc1477912bd35f557808d9, OF8 environmentf46 and
adapter0d2a63b. Documentation/UI revisions do not change those executed identities.

The local gallery retains15views/71targets/12papers and captions, including all
failed baselines, both latest controls, and the declared125ms matched snapshots.
Paper lines and CFD markers retain original axes. Four new refined profile states
have archive SHA2561b67c520969aaaa89c745ba4457ac5d7a025a6e192d9769ceb4dcc7a6352011e;
all440 previously retained T/CO sample hashes match. Image hashes, HTTP delivery
and plotted/history metrics passed; the final PNG was inspected. Raw fields and
reconstruction remain on SCNet, outside Git.

The paper replication remains unresolved. Preserve the failed criteria and current
absolute-Ha coupling. Follow-up should separate transported-Z/momentum behavior,
manifold construction and finer-grid sensitivity with measured controls, rather
than fit chemistry, diffusivity, inlet speed or density to the plotted temperature.
No independent scientific approval, human acceptance or qualified publication is
claimed. The owner deadline remains14November11:59Shanghai; no new execution is
authorized after it.

