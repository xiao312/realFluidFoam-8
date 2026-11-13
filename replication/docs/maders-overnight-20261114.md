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

