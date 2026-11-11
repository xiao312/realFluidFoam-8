# PR-VTA density reconstruction

This module reconstructs density from a retained flamelet T/Y profile. It does
not solve chemistry, alter energy, or establish agreement with the author's code.

Inputs: a GRI30 CSV, Cantera mechanism, critical-property database and output path.
Outputs: PR and translated PR density, per-state EOS residuals, parameter provenance
and a report. The default is a read-only plan; `--apply` writes new outputs.

Müller 2015 Eqs. (8)–(13) define the translation. The mixture Helmholtz stability
addition is omitted, as in that paper. Binary attraction parameters are zero.
The mixture pseudocritical closure is explicitly identified; author mixture input
files are unavailable. A Kay-rule sensitivity accompanies the EOS-equivalent rule.
Minor species without database parameters use declared Lennard-Jones estimates.
No parameter is adjusted against the figure. Pure inlet controls are reported.

Dependencies: Cantera 3.2, NumPy and ruamel.yaml. Inputs remain read-only. There
are no credentials, network calls or scheduler operations. Plotting consumes CSV.

Example: `python reconstruct.py --profile profile.csv --out NEW_DIR --apply`.
Verification: execute the pure-O2 and CH4 endpoints, positive-volume and PR residual
checks, inspect all finite rows, then compare original reference values. A successful
process does not accept the model or its mixture-critical assumptions.
