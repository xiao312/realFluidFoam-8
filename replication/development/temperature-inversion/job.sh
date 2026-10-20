#!/bin/bash
set -euo pipefail
root=${1:?}; release=${2:?}; library=${3:?}; ranks=${4:?}; key=${5:?}; mode=${6:?}; build=${7:?}
[[ -n ${SLURM_JOB_ID:-} && $(realpath -e "$release") == "$root/releases/"* ]] || exit 2
job=$root/jobs/$SLURM_JOB_ID
mkdir -p "$job"/{home,tmp,cache,config,apptainer}
export HOME=$job/home TMPDIR=$job/tmp XDG_CACHE_HOME=$job/cache XDG_CONFIG_HOME=$job/config
cp "$release/SOURCE_REVISION" "$job/source-revision.txt"
cp "$root/builds/$library/SOURCE_REVISION" "$job/library-source-revision.txt"
module load apps/apptainer/1.3.4
image=$root/images/openfoam8-rootfs-7d4e96e0b1a9
sha256sum -c "$image.source.sha256" > "$job/image-verified.txt"
export APPTAINER_TMPDIR=$job/tmp APPTAINER_CACHEDIR=$root/cache/apptainer APPTAINER_CONFIGDIR=$job/config
export APPTAINERENV_RF_JOB_ID=$SLURM_JOB_ID APPTAINERENV_TMPDIR=/work/jobs/$SLURM_JOB_ID/tmp
unset APPTAINER_BIND APPTAINER_BINDPATH SINGULARITY_BIND SINGULARITY_BINDPATH
source_in=/work/${release#"$root/"}
exec apptainer exec --cleanenv --containall --underlay --no-eval --no-mount cwd,hostfs,bind-paths \
 --home "$job/home:/home/foam" --bind "$root:/work" --bind "$release:$source_in:ro" \
 --bind "$job/tmp:/tmp" --workdir "$job/apptainer" --pwd /work "$image" \
 /bin/bash "$source_in/replication/development/temperature-inversion/run.sh" "$source_in" "$library" "$ranks" "$key" "$mode" "$build"
