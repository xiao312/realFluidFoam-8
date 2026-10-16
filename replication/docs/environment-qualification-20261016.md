# SCNet OF8 environment qualification

Date: 2026-10-16, Asia/Shanghai. Status: environment preflight passed on SCNet.
No realFluidFoam build or scientific case has run in this setup stage.

## Inputs

| Input | Identity |
| --- | --- |
| Upstream source | `48506de20ce67f35279c5347b09dcd86865a4c39` |
| Tested environment scripts | `ab1ded37edb474beb77c4d681c792d559baa5708` |
| Runtime-staging scripts | `316151b1d2ee085961948f7e347f312a78b12752` |
| OF8 base image | `openfoam/openfoam8-paraview56@sha256:b307565bb6a8f65be82caa9c552e708eb2888e5e35f90f0b620e6f48b8bfa507` |
| Offline archive SHA-256 | `4ed5497fe0b100ac6e2ad69089b1ba06be77c500fdb2baab81cdce7950b8b8dc` |
| Tested source archive SHA-256 | `15a8da5f396ab036a419c67f7653de633a1480863c28e055adaeaa6063f1550d` |
| Runtime | Apptainer 1.3.4 |
| SIF SHA-256 | `7d4e96e0b1a97a0b361cbaf808b6242fa0c576e5ee2a27cd6a9a514c59cb529e` |
| Runtime format | Directory container extracted from the preserved SIF |

The image's package database identifies OpenFOAM 8 package `20210316`, GCC package
`4:9.3.0-1ubuntu2`, OpenMPI `4.0.3-0ubuntu1`, and make `4.2.1-1.2`.
Live checks confirmed GCC 9.3.0, Open MPI 4.0.3, and
`WM_OPTIONS=linux64GccDPInt32Opt` (double precision, 32-bit labels).

## Attempts and corrections

| Slurm job | Result | Action |
| --- | --- | --- |
| 124582584 | Failed before conversion: helper path used the Slurm spool directory | Resolve helpers from the explicit source release; dispatch regression passed |
| 124582806 | Failed: unsupported compression option in Apptainer 1.3.4 | Use the supported build command under CPU-bound Slurm execution |
| 124583165 | Timed out after 30 minutes and 3 seconds during SIF creation | Do not reuse the incomplete temporary filesystem; raise the next allocation to one hour |
| 124586079 | TIMEOUT at 01:00:09 after SIF creation | Preserved a byte-identical SIF before termination; future conversion limit raised to two hours |
| 124589299 | FAILED 127:0 before OF8 execution | Direct SIF mount denied by site policy; user namespaces disabled; use a directory container |
| 124589444 | COMPLETED 0:0 in 00:06:44 | Extracted preserved SIF once, four CPUs, two-hour limit |
| 124589936 | FAILED 1:0 during OF8 initialization | Source interactive setup using normal shell semantics, then enable strict checks and validate tools |
| 124590012 | COMPLETED 0:0 in 00:00:45 | Probes passed; correct include-list formatting that triggered wmake dependency-scan diagnostics |
| 124590149 | COMPLETED 0:0 in 00:00:44 | Final preflight passed; two CPUs, ten-minute limit |

The archive contains about 114,000 layer entries. The first complete extraction
took about 23 minutes on the shared filesystem. The scheduler denied an in-place
time extension. No scheduler policy or account settings were changed.

## Checks

Passed locally: shell/Python syntax, JSON parsing, recipe pin consistency, local
Markdown links, Slurm spool dispatch, and rejection of an invalid workspace root.
Both the image archive and source archive hashes matched after transfer.

The preserved SIF has 818,364,416 bytes. Its SHA-256 matched the original job output
before termination; its SIF partition table was readable. The timed-out conversion
job is not recorded as successful. Direct SIF launch failed despite a staged
SquashFUSE helper, so the qualified route must use a directory container. Cluster
mount policy and user-namespace settings were not changed.

Passed on SCNet: directory extraction, OF8 identification, compiler/header checks,
`blockMesh -help`, two-rank single-node MPI, and OF8 wmake compile/link/run.
Both MPI ranks reported size 2. The probe printed `OpenFOAM environment probe passed`.
`ldd` resolved `libfiniteVolume.so` from the installed OF8 platform library directory,
with no missing libraries. The final wmake log had no include-scan diagnostics.
Apptainer emitted a deprecation warning for `--underlay`; the job completed normally.
The preflight uses a small generated application with `fvCFD.H` and the installed
finite-volume/mesh libraries. It does not compile the real-fluid solver.

## Reuse this deployment

The runtime is `images/openfoam8-rootfs-7d4e96e0b1a9`, with adjacent `.ready` and
`.source.sha256` receipts. Its source artifact is
`images/openfoam8-124586079-preserved.sif`. Keep both inside the configured root.
The SIF checksum identifies the source image; it is not a per-file integrity
manifest of the extracted directory. Do not edit the directory in place.

With `ROOT` set to the authorized project root, the next build can be planned with:

```sh
SOURCE="$ROOT/releases/ab1ded37edb474beb77c4d681c792d559baa5708"
IMAGE="$ROOT/images/openfoam8-rootfs-7d4e96e0b1a9"
bash "$SOURCE/replication/environment/submit.sh" plan "$ROOT" "$IMAGE" "$SOURCE" build PARTITION
```

Use the private site profile for `ROOT` and `PARTITION`. Review the plan, then
replace `plan` with `apply`. The build has 16 CPUs and a one-hour limit; its duration
and real-fluid targets are not yet qualified. Upstream solver source remains unchanged.

## Records and limits

Raw evidence remains under the configured project root in `logs/` and `jobs/<id>/`.
The successful preflight records the image hash, environment versions, probe output, and
library resolution. Private host profiles and raw host identifiers stay outside Git.
The collected receipt archive is `results/environment-20261016-evidence.tar.gz`,
SHA-256 `fae37ee9f9d4d22f80208c8af7c4fca689146328b4efe0eff2906f39f1b2979f`.
It was copied to the local project state directory with a matching checksum.
The [Lark project record](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf)
contains the dated decisions and work log.

No scientific acceptance follows from environment qualification. The next stage
is the clean realFluidFoam build, then property comparisons, counterflow flames,
and premixed flame speed. Multi-node MPI remains unqualified.
