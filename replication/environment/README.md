# OF8 build and runtime environment

This module owns the pinned base image, project path setup, and bounded Slurm jobs.
It does not launch scientific cases. Inputs are an exact source release and the
base image in `lock.json`. Outputs are job-local receipts, build logs and binaries.

On SCNet, direct SIF mounts are denied by site policy and user namespaces are
disabled. Stage a reusable directory container with `stage-runtime.sh` before
preflight. It extracts the pinned SIF on a compute node, records its hash, and
publishes a ready marker only after extraction succeeds. The directory is an
immutable deployment input; never use `--writable` or edit it in place.

```sh
bash replication/environment/stage-runtime.sh plan ROOT SIF RUNTIME_DIRECTORY PARTITION
bash replication/environment/stage-runtime.sh apply ROOT SIF RUNTIME_DIRECTORY PARTITION
```

All three paths are absolute and inside the project; the runtime directory must
be new and directly under `ROOT/images`. Pass this directory as `IMAGE` below.
Extraction uses four CPUs and a two-hour limit. The original SIF remains the
content reference; the live preflight qualifies its extracted deployment.

Dockerfile and Apptainer.def share the official OF8 image digest. The Dockerfile
adds only metadata and an explicit shell entrypoint. The offline SCNet route imports
the same base filesystem directly; it does not claim an identical derived-image hash.
The execution scripts bypass the image's inherited entrypoint.

## Site preparation

Use `site.example.json` as the schema for a private local profile. It records the SSH
alias, project root, CPU partition, runtime module and resource limits. Scripts take
these values as explicit arguments; they do not read private credentials.
Current job scripts use Apptainer 1.3.4, two CPUs for preflight and 16 CPUs for build.
The time limits are 10 minutes and one hour. Update the scripts and receipt together
if these limits change. No multi-node MPI claim follows from this qualification.

The root must resolve unchanged and end with `/FlamePilot/trials/realfluidfoam`.
On the authorized site it is nested under the existing FlamePilot project root.

```sh
bash replication/environment/workspace.sh plan /absolute/FlamePilot/trials/realfluidfoam
bash replication/environment/workspace.sh prepare /absolute/FlamePilot/trials/realfluidfoam
```

If registry access is unavailable, prepare the pinned image on a connected machine:

```sh
python3 -B replication/environment/prepare_image.py --project-root /absolute/local/project
python3 -B replication/environment/prepare_image.py --project-root /absolute/local/project --apply
```

The first command is read-only. The second verifies compressed blobs and uncompressed
layer hashes, then creates a Docker archive without a Docker daemon. It needs Python 3.11+.
Record the archive SHA-256 and verify it again on SCNet. Keep all intermediate files
under the local project and remote project roots. The workstation Docker disk must
also be on the authorized data drive if Docker is used for image preparation.

Run image conversion on a compute allocation. Set `APPTAINER_TMPDIR`,
`APPTAINER_CACHEDIR`, `APPTAINER_CONFIGDIR`, `TMPDIR`, and all job output paths first.
For an uncompressed Docker archive:

```sh
srun --cpu-bind=cores apptainer build images/openfoam8.sif docker-archive:images/openfoam8-docker.tar
```

Alternatively, use `convert.sh plan|apply ROOT ARCHIVE ARCHIVE_SHA256 PARTITION`
to submit conversion with four CPUs and a two-hour limit. The first 30-minute
allocation timed out during SIF creation on the shared filesystem; incomplete
temporary files from that attempt must not be used as a runtime baseline.
The one-hour retry spent more than 50 minutes extracting and packaging. The
two-hour limit leaves headroom for filesystem variability and temporary-file cleanup.
Pass an absolute archive path under `ROOT/images` to `convert.sh`. Record the resulting SIF
SHA-256; conversion does not have to produce bit-identical SIF metadata on each run.

## Preflight and compilation

Stage a full Git archive as `releases/<revision>` and write its exact commit into
`SOURCE_REVISION`. Upstream contains case-colliding
paths and tracked build artifacts. Do not use a Windows working-tree ZIP.
The build script copies the release into `builds/<job-id>` and removes generated
`lnInclude` and `Make/linux*` directories there. It preserves the source release.

```sh
bash replication/environment/submit.sh plan ROOT IMAGE SOURCE preflight PARTITION
bash replication/environment/submit.sh apply ROOT IMAGE SOURCE preflight PARTITION
```

After preflight passes, use `build` in the same commands. Inspect `jobs/<job-id>` and
`logs/`. The build must produce realFluidFoam, realFluidReactingFoam and reactingFoam.
The library-resolution check must use the job's custom libspecie. Build outputs from
different revisions must not share a user library directory.

Failures stop the job and retain its logs. Do not call the environment ready if the
compiler, headers, MPI smoke test, or required library checks fail. Scientific
acceptance requires the separate property and flame comparisons.

## Verification and boundary

Run `for script in replication/environment/*.sh; do bash -n "$script" || exit; done` and
`python3 -B replication/environment/check_lock.py` from the repository root.
Run `bash replication/environment/check_dispatch.sh /absolute/project/test-output`
to verify dispatch from a simulated Slurm spool directory. The directory must exist.
Runtime preflight compiles an MPI probe and checks two ranks on one node.
It also uses wmake to compile, link, and run a small application against the installed
finite-volume and mesh libraries. This tests the OF8 build environment without
compiling the real-fluid solver or running a scientific case.
Image conversion and compilation require Slurm; login nodes only stage and submit.
Apptainer sees a read-only root filesystem and explicit writable project mounts.
HOME, caches, temporary files, build products, receipts and logs stay within ROOT.
The source release is mounted read-only. The reusable directory container is mounted
without `--writable`; all intended writes use the project binds. Its source SIF hash
and ready marker are checked before launch. Keep the directory immutable between
runs; extract a new directory for an image update. A SIF checksum identifies the
source artifact, not a cryptographic inventory of the extracted directory.
Direct SIF launch failed under site mount policy even with SquashFUSE available;
no cluster security settings were changed.

Dependencies: Bash, Git for release staging, Python for offline image preparation,
Slurm, Apptainer, and the pinned OF8 container. Future case modules depend on these
qualified outputs. No host OpenFOAM or MPI module is loaded.
