# Liang et al. (2019) Fig. 1 — density and thermal conductivity of O2 at 100 atm

Target `liang-1` of the V&V ladder. The published figure compares a real-fluid model with
NIST data for pure oxygen at 100 atm: panel (a) density, panel (b) thermal conductivity,
both from 200 K to 1000 K.

* Liang, Li, Law (2019), *Proc. Combust. Inst.* 37, doi `10.1016/j.proci.2018.06.070`
* paper PDF sha256 `24163be0124e0fa6cd28ddb1d369b813e64e82bd7446e9f9218a340445aca6fe`
* Fig. 1 = page 3 of the PDF; the figure itself is an **embedded JPEG raster**
  (DeviceGray, 775x1371 px, sha256 `b28ef871c4ad92031d7eeaf24e8a20d0fde6e83f9842c88c0f98ea645068c9ea`),
  so every published reading is a pixel measurement, not a vector path.

## What is compared

| series | origin |
| --- | --- |
| `paper-model` | model curve of Fig. 1, digitised from the embedded raster (this directory) |
| `paper-experiment` | filled triangles of Fig. 1, digitised from the same raster (NIST data as plotted) |
| `computed` | SRK density and Ely–Hanley conductivity at 100 atm, from repository source |

The paper states that its transport model uses the Ely–Hanley correlation for thermal
conductivity and the Takahashi high-pressure correction for binary diffusion.  Panel (a)
does not name the equation of state; the density model is therefore compared with **SRK**
(`../cantera-liang/SrkKernel.h`) and, as a cross-check, with the Peng–Robinson
implementation of `../oxygen-properties/oxygen_properties.py`.  Both are computed here;
the report states which one the paper's own numbers agree with.

## Method

`fig1_probe.cpp` (header-only, no Cantera SDK, one thread) evaluates

* SRK volume and residual `cp` from `liang::evaluate` (`../cantera-liang/SrkKernel.h`,
  molar SI units: kmol, m3, K, Pa, J);
* thermal conductivity from `rfElyHanley::conductivity`
  (`../liang-properties/ElyHanley.H`), pure O2 with `cp_R` from the ideal-gas fit;
* ideal-gas `cp` from the NIST Shomate fit of O2, lower range 100–700 K and upper range
  700–6000 K, with the 700 K splice written to stderr (`shomate_join_700K`) so the join
  can be verified rather than assumed.

O2 constants (Liang et al. Fig. 1 conditions): `Tc = 154.581 K`, `Pc = 5.043 MPa`,
`Vc = 0.0734 m3/kmol`, `W = 31.9988 kg/kmol`, `omega = 0.022`, `p = 100 atm = 10.1325 MPa`.

`digitize_fig1.py` measures the published figure with the Python standard library only:

1. the axis calibration of `../liang-properties/figure1-calibration.json` is **re-fitted**
   from its own tick lists and the residuals reported (worst tick residual below 1 px);
2. filled triangles are found from 3x3-erosion cores, which rejects the 2–3 px model line
   and the inward axis ticks (a core must be 5x5 px or larger and roughly isotropic);
3. the triangle cores and their rims are removed, the remaining line mask is thinned with
   Zhang–Suen, and each ridge component is walked into an ordered polyline, so steep
   branches are traced correctly instead of being flattened to one value per column;
4. a break in the ridge is kept as a **gap**, never interpolated: the model line is hidden
   where a filled symbol is printed on top of it.  The gaps are listed in the output and
   drawn as separate segments in the plot.

## Uncertainty and limitations

* 1 px is about 1.19 K and 0.38 kg/m3 horizontally/vertically in panel (a), and about
  1.34 K and 2.3x10^-4 W/(m K) in panel (b).  Line centre and triangle centre add about
  1 px and 2 px respectively; the totals are reported per series in the evidence.
* Panel (a): the digitised model curve starts at **238 K**, because below that the curve is
  drawn against the axis frame and its inward ticks and cannot be separated from them in
  the raster.  Panel (b): the model peak is **cut off by the top frame** (about
  0.155 W/(m K)); only the clipped maximum is readable.
* The published axes carry no minor ticks that survive the raster, and the raster has no
  vector text, so the reproduction draws the axis labels from the measured positions
  (`labels` in the recipe) instead of glyph paths.  Tick values and limits follow the
  fitted calibration, not the artist's original layout.
* Fig. 1 alone cannot separate the paper's equation of state from its transport model; the
  report therefore reports both EoS candidates and does not claim that either one is the
  author's.

## Reproduction

```sh
sh job.sh "$PWD" /path/to/run-dir          # build + probe, writes fig1-probe.csv
python3 digitize_fig1.py --rgba fig1.rgba \
    --calibration ../liang-properties/figure1-calibration.json --out digitised.json
node render_figures.mjs --probe run-dir/fig1-probe.csv --digitised digitised.json --out out-dir
python3 checks.py --probe ... --digitised ... --out verification.json
```

`fig1.rgba` is the decoded raster of the embedded JPEG, produced by
`node tools/jpeg2raw.mjs` (`@napi-rs/canvas`); its sha256 is recorded in the digitisation
output.  Nothing here writes into the repository at run time.
