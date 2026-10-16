#!/bin/bash
set -eo pipefail
root=${1:?root}; image=${2:?SIF}; runtime=${3:?runtime directory}; helper=${4:?workspace helper}
test -n "${SLURM_JOB_ID:-}"
bash "$helper" plan "$root" >/dev/null
[[ -f "$image" && $(realpath -e -- "$image") == "$root/images/"* ]] || exit 2
[[ $(realpath -m -- "$runtime") == "$runtime" && $(dirname -- "$runtime") == "$root/images" ]] || exit 2
[[ ! -e "$runtime" && ! -e "$runtime.ready" ]] || exit 2
job="$root/jobs/$SLURM_JOB_ID"
mkdir -p "$job"/{tmp,home,config,cache}
export APPTAINER_TMPDIR="$job/tmp" APPTAINER_CACHEDIR="$job/cache"
export APPTAINER_CONFIGDIR="$job/config" TMPDIR="$job/tmp" HOME="$job/home"
module load apps/apptainer/1.3.4
cd "$root"
sha256sum "$image" > "$runtime.source.sha256"
apptainer --version > "$job/apptainer-version.txt"
srun --cpu-bind=cores apptainer build --sandbox "$runtime" "$image"
test -f "$runtime/opt/openfoam8/etc/bashrc"
sha256sum -c "$runtime.source.sha256"
printf 'source job=%s\n' "$SLURM_JOB_ID" > "$runtime.ready"
echo 'PASS: SIF extracted to reusable runtime directory' > "$job/result.txt"
