# Author thermochemistry inputs

These files are copied from the author's OF8 thermophysical-library repository at
the revision in `provenance.json`. That manifest records original Git-file bytes,
stored hashes, and paths. Only CRLF-to-LF conversion and removal of trailing horizontal whitespace were applied. The parent
repository's GPL-3.0 license applies. No paper PDFs or private data are included.

`thermo.inputData_GRI` and `reactionsGRI` define the released 53-species GRI30
counterflow inputs. `property-thermo.inputData` contains the released property-test
coefficients. The property generator extracts the CH4 dictionary from that file;
it does not assume rounded tutorial coefficients equal other GRI30 distributions.

Consumers: case generation and the property probe. Verification: compare each
stored SHA-256 with `provenance.json` before generating cases. Outputs belong in
the supplied job directory; these input files are never edited during execution.
