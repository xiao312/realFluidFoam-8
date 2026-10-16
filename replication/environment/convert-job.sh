#!/bin/bash
set -eo pipefail
root=${1:?root}; archive=${2:?archive}; digest=${3:?digest}
test -n "${SLURM_JOB_ID:-}"
script_dir=${4:?absolute source environment directory}
bash "$script_dir/workspace.sh" plan "$root" >/dev/null
[[ $(realpath -e -- "$archive") == "$root/images/"* ]] || exit 2
job="$root/jobs/$SLURM_JOB_ID"
[[ $(realpath -m -- "$job") == "$job" ]] || exit 2
mkdir -p "$job"/{tmp,home,config,cache}
export APPTAINER_TMPDIR="$job/tmp" APPTAINER_CACHEDIR="$job/cache"
export APPTAINER_CONFIGDIR="$job/config" TMPDIR="$job/tmp"
module load apps/apptainer/1.3.4
cd "$root"
printf '%s  %s\n' "$digest" "$archive" | sha256sum -c -
gzip -dc "$archive" > "$job/openfoam8-docker.tar"
env HOME="$job/home" apptainer build --mksquashfs-args '-processors 4' \
    "$job/openfoam8.sif" "docker-archive:$job/openfoam8-docker.tar"
[[ ! -e "$root/images/openfoam8.sif" ]] || exit 2
mv "$job/openfoam8.sif" "$root/images/openfoam8.sif"
sha256sum "$root/images/openfoam8.sif" > "$root/images/openfoam8.sif.sha256"
echo 'PASS: offline archive verified and converted' > "$job/result.txt"
