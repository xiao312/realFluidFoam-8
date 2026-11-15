# G2 temperature-field references and retained simulation fields

Four published simulation targets supplement the existing G2 profiles and optical
morphology targets. The actual retained5ms fields are also rendered. This work
adds no simulation, changes no physics and grants no scientific acceptance.

| Source | Target | What it measures or predicts |
| --- | --- | --- |
| Müller and Pfitzner2015 | Fig.6(a), PDFp.8 | Instantaneous G2 LES temperature section;5.61MPa, O2/CH4at85/288K,44.4/143.1g/s. |
| Cavalieri et al.2025 | Fig.10(a), PDFp.13, upperTF | Instantaneous G2/TF temperature;56.1bar,85/288K,44.4/143.1g/s. LowerDTF case is not this target. |
| Cavalieri et al.2025 | Fig.11(a), PDFp.14, upperTF | Time-averaged temperature withSFM/MFM mixing models. Current instantaneous fields are previews, not a mean. |
| De Giorgi et al.2014 | Fig.4(a), PDFp.11 | G2 RANS temperature fields for twoEDC mechanisms,5.6MPa,85/288K. Accompanying experimental backlight is not thermometry. |

Each supplied PDF and caption was read. Selected panels and original captions
were rendered separately and visually inspected. The target registry records
PDF hashes, page/crop coordinates, conditions, statistics and plotting plans.
Use actual spatial scales and preserve aspect ratio. Keep current cell values
piecewise constant. Do not smooth a field to resemble turbulent LES structures.
Instantaneous LES fields require morphology and ensemble statistics, not matching
each eddy or a pixelwise temperature RMS. Quantitative image-temperature scoring
requires a separately calibrated color map and documented digitization.

## Experimental boundary

The checked [Singla2005 G2 experiment](https://doi.org/10.1016/j.proci.2004.08.063)
provides OH*/CH* emission and backlighting. Existing Fig.4(c,d) andFig.5(b) remain
morphology targets. Emission brightness is not a calibrated temperature field.
Schmitt2020 Fig.19(c) is a simulated2000K isosurface colored by velocity; Fig.22
is for hydrogen casesA60/C60, not methaneG2. Neither is a new G2 temperature map.
Sharma2023's later multi-element temperature images are also not the single G2
validation geometry. These distinctions prevent inappropriate figure matching.

[Grisch et al.2011 CARS measurements](https://www.eucass.eu/component/docindexer/?id=4440&task=download)
provide genuine experimental temperature profiles on MASCOTTE V05, but at1MPa
with gaseous room-temperature reactants and mixture ratios1/2. They are a useful
separate thermometry benchmark, not the5.6MPa cryogenicG2 case. This search did
not verify a direct experimental2D temperature map for the exactG2 condition.
That is a search limitation, not a claim that none exists.

## Current field reconstruction

Two read-only selected collections transferred about1.59MB total fromSCNet to
the local project drive. No remote writes or new allocations were required.
The renderer verifies every original input hash and maps32partition addressing
lists onto the original mesh. Every global cell is assigned exactly once.
The meridional polygons come from actual cell vertices projected into axial and
radial coordinates. No interpolation, smoothing or evolved CFD restart occurs.

| Case | Job | Cells | Global temperature maximum | Cell-center location |
| --- | --- | --- | --- | --- |
| Schmitt settings |128079165|20000|1983.9918K|x21.5mm,r2.725mm|
| Cavalieri settings |128079711|10000|2215.1142K|x23.5mm,r2.91mm|

Both are5ms instantaneous fields. Earlier reported near-axis maxima were792.6K
and738.0K. Those line samples are not global field maxima and cannot establish
extinction. The hot region is off-axis. This is additional evidence from the
same completed calculations, not new flame performance or a passed paper target.

The cases still use53transported species and mixture fraction withCr100
relaxation toward a finite-strain table. They do not reproduce the full LES/PDF
model or developed statistics of the references. Original solver, library, case,
table and environment hashes remain in the collection and execution receipts.
Global energy and elemental qualification remain open.

## Sources and reproduction

- [Müller and Pfitzner2015, EUCASS018](https://www.eucass.eu/component/docindexer/?id=3841&task=download).
- [Cavalieri et al.2025](https://doi.org/10.1016/j.ijheatmasstransfer.2025.127284).
- [De Giorgi et al.2014, open-access publisher text](https://www.mdpi.com/1996-1073/7/1/477).
- [Schmitt2020](https://doi.org/10.1007/s10494-019-00096-y).
- [Sharma et al.2023 author manuscript](https://arxiv.org/abs/2311.15034).

Run the field module's documented plan and renderer against the explicit local
collection root. Actual rendering checked20000/10000cells and all32partitions
for both runs. Original field archives, NPZ cell data, PNGs and hash receipts
remain outside Git. The existing central Forge catalogue owns the added target
entries. Existing71targets and all their results/captions must remain intact.
