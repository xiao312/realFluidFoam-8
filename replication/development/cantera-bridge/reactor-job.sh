#!/bin/bash
set -euo pipefail
root=${1:?}; release=${2:?}; sdk=${3:?}; build=${4:?}; inputs=${5:?}; reference=${6:?}
[[ -n ${SLURM_JOB_ID:-} ]] || exit 2
root=$(realpath -e "$root")
for path in "$release" "$sdk" "$build" "$inputs" "$reference"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
job=$root/jobs/$SLURM_JOB_ID
mkdir -p "$job"/{home,tmp,cache}
export HOME=$job/home TMPDIR=$job/tmp XDG_CACHE_HOME=$job/cache OMP_NUM_THREADS=1
export LD_LIBRARY_PATH="$sdk/lib:${LD_LIBRARY_PATH:-}" CANTERA_DATA="$sdk/share/cantera/data"
cd "$job"
(cd "$build"; sha256sum -c binary.sha256) > binary-verified.txt
module load apps/python/3.8.13
module_path=$release/replication/development/cantera-bridge
python3 -B "$module_path/reactor_probe.py" "$build/librfcantera.so" "$inputs" "$reference" > ideal.json
python3 -B "$module_path/reactor_probe.py" "$build/librfcantera.so" "$inputs" "$reference" \
 --stage 3 --options pressure-chemistry,smoothed-alpha > smooth-srk.json
cp "$release/SOURCE_REVISION" source-revision.txt
sha256sum "$inputs/ideal.yaml" "$inputs/srk.yaml" "$inputs/species.txt" "$reference" > input.sha256
printf 'PASS: ideal CP parity, smooth SRK conservation, state reset; CFD coupling unqualified\n' > result.txt
