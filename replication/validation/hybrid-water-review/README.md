# Hybrid water-progress physical review

This offline renderer reviews the approximate quench plus homogeneous-chemistry
manifold produced by `fgm/hybrid-water`. It shows measured cap signs, temperature
and source surfaces, representative retained chemical trajectories, independent-Z
interpolation errors and projected versus detailed chemical energy sources.
It does not accept a table, rewrite data, integrate chemistry, publish a page or
claim reproduction of Sharma's different mechanism, pressure and progress variable.

Inputs are an immutable result directory with `receipt.json`, `diagnostics.json`,
`heldout.json`, `table.npz`, and optionally selected `z-NNN` physical branch/tail
arrays. The receipt must bind the table and summary hashes. Each retained branch
is checked against its case receipt; optional raw tails are hashed in the output
manifest. For a separately derived table, `--physical-input DIR` supplies the
original branches and must match the derivation's original receipt hash. Missing
optional branches are omitted rather than fabricated. The output
directory must be new. `--plan` reads identities without creating files.

Dependencies are Python, NumPy and Matplotlib. The physical driver provides
inputs; the human review gallery consumes PNG/SVG figures, HTML and a manifest.
There is no scheduler, network, secret, CFD or model-provider dependency.

Example:

```sh
python replication/validation/hybrid-water-review/render.py \
  --input /retained/hybrid-water-r1/run --out /new/review --plan
python replication/validation/hybrid-water-review/render.py \
  --input /retained/hybrid-water-r1/run --out /new/review
```

Verification uses the actual retained physical result, checks its hashes, renders
all figures, then visually inspects axes, units, legends and visible limitations.
Plots use actual tabulated samples and recorded branch order. No smoothing,
source clipping, automatic scientific pass or hidden normalization is introduced.
