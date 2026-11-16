# G2 / Maders setup follow-up

16 November2026,10:37 Asia/Shanghai. This is a checkpoint, not science approval.
See [the primary-source audit](../docs/g2-maders-setup-audit-20261116.md).

## Completed

- Sourcece66c0b adds a separate tapered G2 injector diagnostic and independent
  Maders field/table audit. Sourcef6e2ae8 corrects the confirmed Maders slip wall.
  Both development commits were pushed and the remote branch verified.
- Mesh job128161149 completed341s,2ranks,Slurm0:0. Actual blockMesh/checkMesh:
  10720cells,21861points,42970faces; maximum nonorthogonality9.39135degrees,
  aspect ratio20.2173 and skewness0.439413; `Mesh OK.`
  This qualifies the generated wedge topology, not the square-chamber LES.
- R19 fine-grid independent audit at1.11500646592s: all498radial samples covered;
  hot CFD-minus-table temperature RMS0.395344/0.257401K at10/40mm. This does not
  establish paper agreement. Stored diagnostic fields are stale and excluded as
  a source-validity witness. Wrong expected table SHA256 failed as required.
- Actual retainedR19/0/U confirms `outerWall { type slip; }`. Verhoeven thesis
  PDFp44 requires no-slip. The corrected generator records its explicit selection;
  local paired generation differs only in0/U among physical dictionaries.
- Added the audit as a local Forge alternate view, retaining all75targets,
  12papers, original captions and primary comparison images. Updated candid
  G2 setup notes. Three HTTP byte checks passed. No external scientific publication.

## Physical correction running

Maders job128162325, key `maders-noslip-a02-f6e2ae8`,32ranks/64GiB/5400s,
was admitted through the FlamePilot adapter. It uses recipe
`f6e2ae80116b0ea46c58ecfc3660bc1bdf2bcb54`, compiled solver
`ea2a4046ab239ae4fdb1197cd65fd83ebc933785` and original table SHA256
`35a6b46b5a56d2831a598acb7810119b6bc27ced27d90d217d2258514295c1cc`.
SameR19 inlet,1000axial cells,0.9s scheduled ignition andZ range0.04–0.30;
requestedend1.1s. Initial fields are freshly generated at0, not donor CFD fields.
The executing OF8 dictionary check confirmed `noSlip`; actual initial solver
time4.36799246899e-7s and temperature297.97869–298.05124K were observed.
These are cold-start evidence, not combustion survival or improved paper match.

Both jobs use the retained qualifiedOF8 profile SHA256
`f46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793`,
binding `8e158ebd26a0a8699ce24c074540333755abce62495b54e1cb0d9d58073ea1ee`,
and FlamePilot HPC source `0d2a63b546e180facdb6f1c736077517daa5c78c`.
No new C++ runtime build is claimed for the case-only wall correction.

The prior overnight campaign remains closed with its122jobs/1261.891111
allocatedcorehours recorded. This separate owner-requested follow-up has two
new admissions; it does not reset historical consumption. Its operator-selected
cutoff is2026-11-16T12:11:36+08:00. No old trial was reopened.

The mesh submission first failed locally with Windows WinError206 beforeSSH
creation. After exact remote-directory and scheduler absence reconciliation,
the same retained admission completed via binarySSH stdin. A read-only CRLF
transport failure was also preserved. Strict Bash, source and environment
identities were not weakened. Only small source/evidence files moved directly
between this workstation andSCNet; noECS bulk transfer or unrelated job change.

## Remaining development

The currentG2 Y(Z)-relaxation model must not be labelled finite-rateFGM. Separate
equilibrium/steady-flamelet and raw-progressFGM controls. Qualify scalar
dissipation dependence, manifold coverage and table/CFD enthalpy consistency;
then explicit local ignition, inlet-flow development and turbulence/statistics.
Keep failed and startup comparisons visible. A fresh no-slip coflow result and
the injector mesh qualification alone cannot establish a solvedG2 flame.

Detailed raw receipts, reconciliation and current exact job status live outside
Git in `state/g2-fgm-setup-audit-20261116/OPERATOR.md` and `maders-followup/`.
