#!/bin/bash
# Run only in an allocation. Use explicit paths and a clean container environment.
set -euo pipefail
root=${1:?root}; image=${2:?image}; source_dir=${3:?source}; mode=${4:?preflight or build}
[[ "$mode" == preflight || "$mode" == build ]] || exit 2
[[ -n ${SLURM_JOB_ID:-} ]] || { echo 'Run this script through Slurm' >&2; exit 2; }
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
bash "$script_dir/workspace.sh" plan "$root" >/dev/null
for path in "$image" "$source_dir"; do
    [[ $(realpath -e -- "$path") == "$root/"* ]] || { echo "Path outside project: $path" >&2; exit 2; }
done
job="$root/jobs/$SLURM_JOB_ID"
[[ $(realpath -m -- "$job") == "$job" ]] || exit 2
mkdir -p "$job"/{home,tmp,vartmp,cache,config,apptainer}
export APPTAINER_TMPDIR="$job/tmp" APPTAINER_CACHEDIR="$root/cache/apptainer"
export APPTAINER_CONFIGDIR="$job/config" TMPDIR="$job/tmp"
unset APPTAINER_BIND APPTAINER_BINDPATH SINGULARITY_BIND SINGULARITY_BINDPATH
export APPTAINERENV_HOME="/work/jobs/$SLURM_JOB_ID/home"
export APPTAINERENV_TMPDIR="/work/jobs/$SLURM_JOB_ID/tmp"
export APPTAINERENV_XDG_CACHE_HOME="/work/jobs/$SLURM_JOB_ID/cache"
export APPTAINERENV_XDG_CONFIG_HOME="/work/jobs/$SLURM_JOB_ID/config"
export APPTAINERENV_RF_JOB_ID="$SLURM_JOB_ID"
export APPTAINERENV_RF_CPUS="${SLURM_CPUS_PER_TASK:-2}"
sha256sum "$image" > "$job/image.sha256"
apptainer --version > "$job/apptainer-version.txt"
# Prior SCNet qualification observed runtime cleanup of SIF launch copies.
# Retain the master image and execute a job-local copy.
cp --reflink=auto "$image" "$job/runtime.sif"
source_in="/work/${source_dir#"$root/"}"
cd "$root"
exec apptainer exec --cleanenv --containall --underlay --unsquash --no-eval \
    --no-mount cwd,hostfs,bind-paths --home "$job/home:/home/foam" \
    --bind "$root:/work" --bind "$source_dir:$source_in:ro" \
    --bind "$job/tmp:/tmp" --bind "$job/vartmp:/var/tmp" --workdir "$job/apptainer" \
    --pwd /work "$job/runtime.sif" /bin/bash \
    "$source_in/replication/environment/inside.sh" "$mode" "$source_in"
