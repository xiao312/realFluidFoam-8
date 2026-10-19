# Pressure-chemistry comparison, 20 October 2026

At 01:07 Asia/Shanghai, Cases 2 and 3 had passed numerical screening at all
13 equivalence ratios. Against the ten matching paper markers, their RMS
differences were 0.0133 and 0.0077 cm/s. The eight completed matching Case 4
points gave 0.0115 cm/s RMS. The partial Case 5 curve was still high at the
rich end: +0.0993 cm/s at phi=1.35 and +0.1120 cm/s at phi=1.40.

The comparison screen, specified before the full-curve evaluation, is
`abs(error) <= max(0.05 cm/s, 0.01*reference) + digitization uncertainty`.
Raster uncertainty is 0.015–0.04 cm/s. No extrapolation is used; marker series
are compared only at matching nominal phi. These are numerical comparison
screens, not scientific acceptance or proof of Liang's unpublished model inputs.

The plot contains 51 screened points: 12 existing ideal controls and 39 new
pressure-chemistry points. It replaces the existing Lark gallery in place,
retaining the paper panel, caption and physical size. The plotter corrects the
axis calibration using measured tick centers; this does not alter solved speeds.
The black-curve digitizer excludes the y-axis tick region before sampling.

## Takahashi table discrepancy

The primary [Takahashi paper](https://doi.org/10.1252/jcej.7.417), Table 2 on
printed page 419, specifies **B=2.39031 at Pr=3.0**. Cantera v3.2.0 instead has
3.39031 in `src/transport/HighPressureGasTransport.cpp`. Nguyen's upstream
`chungTakaTransportI.H` has the primary value 2.39031. The downloaded primary
PDF SHA256 is `88e9eaa011e6b17b4ea2dd1253c36e363865776f4c8a8fa4db8fb507ada3945e`;
the table was checked visually as well as by text extraction.

At Pr=3 and Tr=2, the original Cantera function gives 0.991467; Table 2 gives
0.941602. The regression first reproduces that discrepancy, then passes with
the isolated `takahashi-table2` option. Other pressure rows and interpolation
continuity remain checked. No parameter has been fitted to a flame curve.
This option preserves the existing reduced-temperature bounds and changes only
the one coefficient's contribution. Both forms remain available for comparison.

Source/build 8a0c8d0/124940280 passed on SCNet. Case 5 correction pilots:

| phi | Pressure (atm) | Job |
| ---: | ---: | --- |
| 1.00 | 100 | 124940384 |
| 1.10 | 100 | 124940385 |
| 1.40 | 100 | 124940386 |
| 1.10 | 1 | 124940387 |

The flame effect is pending at this checkpoint. The full retained pressure sweep
uses cf40834/build124937336. Added phi=1.02 conditions use a10cd1b/build124938314.
The ideal phi=1.02 job 124938861 failed before entering the solver because site
Bash treats an empty array as unbound under nounset. Source96ba5de fixes the
wrapper; retry124940112 uses build124939982. The failed receipt remains retained.

## Energy and CFD follow-up

Smooth-alpha Case 3 pilots 124939642/124939652 completed in about six minutes.
Physical-concentration and pressure-chemistry speeds are 6.910495 and 7.027479
cm/s, respectively. Energy audit124940475 compares their frozen fluxes with
the original-alpha controls. See the separate enthalpy-discontinuity record.

All twelve original-zero 200-us CFD jobs completed. For phi=1.10, 180–200-us
mean OH speeds are 7.2022 cm/s for native124916221 and 7.3970 for corrected
124916226. Temperature-marker means are 7.0838 and 7.2596. Both markers still
drift upward; a final OH sample near7.45 is not a steady convergence result.

Source6d22c3e launches the corrected binary124900963 at all eleven CFD phi
conditions and the native binary124883260 at phi1.10 to **300 us from newly
generated original-zero fields**. It does not resume the completed runs.
The phi1.10 pair has matching physical-input hash
`b61cf0f9c15769e9f1e391803996285b46e2ca4486389a5c13f7c7b0a8b8aa3f`.
Jobs124939589/594/600/606/611/614/620/636/647/655/658 are the corrected phi
0.90–1.40 sweep; job124939663 is the native control. Each uses eight cores and
an eight-hour ceiling. All twelve were running with verified time-zero starts.

No corrected production solver merge or new 2D campaign is justified by these
partial 1D data yet. Remaining checks include time/mesh/domain independence,
the model-specific energy balance, and the full corrected diffusion curve.
