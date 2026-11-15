# Resolve an OpenFOAM written-time directory

This read-only helper maps a full-precision physical time to one actual written
directory. It does not advance or restart CFD, choose a latest state, interpolate
fields, change scientific tolerances, submit jobs, or write case files.

`resolveWrittenTimeDirectory({processorDirectory, physicalTime, precision, format})`
requires a finite nonnegative time, explicit output precision (1–17), and one of
`general`, `fixed`, or `scientific`. These settings must come from the case's
`controlDict`. It returns the unique existing numeric directory within that
format's rounding interval, its path, difference and rounding bound. Zero or
multiple matches fail with the searched directory and expected serialization.
The helper never chooses an arbitrary nearest time.

It uses Node's filesystem/path modules only. Qualification readers may copy this
file with an exact Git/source hash. The scientific solver and scheduler do not
depend on it. It reads directory entries, handles no credentials, and makes no
network calls. The caller owns the filesystem access boundary.

```js
import {resolveWrittenTimeDirectory} from './resolve.mjs';
const written = resolveWrittenTimeDirectory({
  processorDirectory: '/workspace/cases/control/processor0',
  physicalTime: 0.000122526603025096,
  precision: 12,
  format: 'general'
});
// The observed case directory is 0.000122526603025, not the log's full number.
```

Verification: `node --check replication/validation/written-time/resolve.mjs`,
then a Slurm verification-only replay against the retained real R68b failure.
Require the same directory on all 32 ranks, all field hashes, normal-control
parity, and logged/written-density agreement. The original failed allocation
and its faulty-reader receipt remain unchanged. Resolver success is not a
scientific acceptance decision.
