# Streaming input for long G2 diagnostics

This module reads complete retained solver logs without constructing one JavaScript
string. It preserves raw bytes through a full-file SHA256, original line numbers,
every record used by the registered G2 checkers, malformed values and failure
markers. It supplies input records; it changes no scientific criterion, equation,
case, scheduler operation or acceptance decision.

`scanSolverLog(path, limits)` is read-only. It returns `lines(prefix)`,
`markerText`, `times`, and `identity`. Callers retain their original record parsers.
`identity` records source bytes/SHA256, line counts, per-prefix record counts,
retained bytes and original line mappings. The underlying file must stay unchanged
through the complete read. Scientific records are stored as individual lines,
so there is no concatenated scientific-log string or Node single-string limit.

Default explicit bounds:1MiB per line,1.5million retained records,512MiB total
retained record text,4MiB marker text. Exceeding a bound or a changed source
throws; no record is silently dropped. Limits must be projected from an actual
short run before using a longer case. These are memory guards, not scientific
acceptance thresholds. Malformed/nonfinite values are not sanitized.

`writeJson(path,value)` writes plain scientific JSON objects/arrays incrementally,
preserving their `JSON.stringify(value,null,2)` representation without building
the whole result string. Dates, custom `toJSON` methods, functions and symbols
are outside this report interface.
It refuses an existing output. A failed write leaves evidence at that path.

Inputs are local log paths and explicit limits. Outputs are in-memory records,
identity metadata and optional caller-selected JSON files. Dependencies are Node
built-ins. Consumers are direct-fgm/check.mjs and separately identified operator
endpoint/density/projection/conservation adapters. There is no solver dependency,
secret, network operation or untrusted code evaluation.

Example: `node inspect.mjs /absolute/case/log.solver` prints compact counts and
the full raw-log identity. Verification uses `node test.mjs NEW_FIXTURE_DIRECTORY` for dimension,
invalid-record retention and JSON equivalence, followed by the required actual
short-log all-metric/all-verdict parity in the operator qualification packet.
Synthetic checks do not qualify physical results.

`qualify.mjs CONFIG --apply` is a bounded Slurm postprocessing-only regression
on the complete retained100us log. It compares all direct/endpoint/density/
projection/conservation report metrics and verdicts, exact original conservation
line mappings and CSV bytes, both audit wrappers, and required-record refusal.
Its shadow directories link retained fields for reading; no CFD is executed or
restarted. The original packets and case remain unchanged. Without `--apply`
the command prints its read-only plan.

`operator/` contains narrowly adapted copies of the frozen composite evaluators.
`operator/origins.json` identifies every original and adapted file. The fixed-mesh
conservation core is byte-identical. The adapters use original record conversion
and criteria, scalar reductions instead of spread maxima, and incremental JSON/
CSV output. The wrapper reads the directly emitted small summary, never the full
report back into one string. These are evaluator changes, not scientific approval.
