# Paper-specific conditions and coordinate interpretation

This record follows the downloaded paper text and rendered geometry drawings,
not previous shorthand descriptions of the legacy mesh. PDF identities are in
`reference-geometry.json`.

| Target | Pressure / inlet temperature | Injector / domain | Important distinction |
| --- | --- | --- | --- |
| Mueller 2015 Figures 6-7 | 5.61 MPa; O2 85 K, CH4 288 K | O2 duct 3.6 to 5 mm; CH4 diameters 5.6/10 mm; full 50x50 mm square, 150 mm simulated length | Tapered O2 duct retained; methane inlet placed at exit; precursor LES inlet turbulence |
| Cavalieri 2025 TF Figure 6 | 56.1 bar; 85/288 K; 44.4/143.1 g/s O2/CH4 | Same 3.6-to-5 mm O2 duct and 0.3 mm radial lip; CH4 5.6/10 mm; square 50 mm, length 200 mm | TF only; DTF changes CH4 to 120 K and outer diameter 7.29 mm; 60 ms statistics after flushing |
| Sharma 2023 G2 Figures 4/9 | 5.61 MPa; 85/288 K | d1/d2/d3/d4=3.6/5/5.6/10 mm; 10 degree LOx divergence; square 50 mm, length 200 mm | Paper prose swaps the two mass flows despite O/F=0.31; supplied velocities do not consistently match mass/area |
| Schmitt 2020 Figure 21 | Section 3 states 56 bar G2, O2 83 K / methane 300 K | Actual tapered lip; full square 50x50 mm chamber, length 400 mm | Not exactly the 85/288 K condition; 50 ms Reynolds statistics after one convective time |

Mueller page 7 Table 2 gives O2=44.4 g/s and CH4=143.1 g/s. Cavalieri page 8
Table 2 independently gives those same rates. They are the declared TF diagnostic
mass-flow basis. At the paper densities 1180/42 kg/m3 and the 5 mm O2 exit, these
imply approximately 1.916/63.20 m/s at the two exits. The O2 upstream 3.6 mm
diameter instead gives 3.697 m/s. Cavalieri quotes 3.70 m/s alongside VR=33 and
J=39, but those ratios agree with the smaller exit velocity, not 3.70 m/s. Treat
this as a section/label inconsistency rather than changing flow to force all
numbers to match. Sharma's 2.48 m/s O2 entry and swapped mass-flow prose are also
not a basis for silently changing the conserved mass-flow inputs.

The canonical legacy geometry was measured from registered boundary/points/faces
bytes, excluding the huge wedge surfaces. The oxygen radius is 1.6 mm from raw
x approximately 0 to 5 mm and increases to 2.5 mm at raw x=10 mm. Its methane
duct runs from raw x=0 to 10 mm with radii 2.8/5 mm. The wall at the end has a
separator band 2.5-2.8 mm and an outer rim 5-6.5 mm. This supports identifying raw
10 mm as the injection exit. A paper profile 15/45/70 mm downstream would use
legacy raw x=25/55/80 mm, whereas this new exit-origin mesh uses 15/45/70 mm.

The new recipe intentionally matches exit areas only. It does not reconstruct
the papers' upstream taper from a guessed length or use an axisymmetric wedge
as evidence for a square-chamber LES. The already qualified R=1.6 mm co-planar
mesh remains useful for short numerical checks under its original identity.
