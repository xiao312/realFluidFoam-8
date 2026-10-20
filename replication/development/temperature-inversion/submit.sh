#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; library=${4:?}; ranks=${5:?}; key=${6:?}
mode=${7:?}; build=${8:-none}; parity=${9:-none}
[[ $action == plan || $action == apply ]] || exit 2
[[ $library =~ ^[0-9]+$ && ( $ranks == 8 || $ranks == 32 ) ]] || exit 2
[[ $mode == build || $mode == full ]] || exit 2
[[ $key =~ ^phi(090|095|100|105|110|115|120|125|130|135|140)$ ]] || exit 2
root=$(realpath -e "$root")
[[ $root == */FlamePilot/trials/realfluidfoam && $(realpath -e "$release") == "$root/releases/"* ]] || exit 2
grep -q '^PASS: build,' "$root/jobs/$library/result.txt"
if [[ $mode == full ]]; then
 [[ $build =~ ^[0-9]+$ ]] || exit 2
 grep -q '^PASS:' "$root/jobs/$build/result.txt"
 python3 - "$root" "$library" "$ranks" "$build" "$parity" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);library,ranks,build,parity=sys.argv[2:]
meta=json.loads((root/'jobs'/build/'thermo-inputs.json').read_text())
assert meta['library_job']==library and meta['mpi_ranks']==int(ranks) and meta['mode']=='build'
if ranks=='32':
    assert parity.isdigit(), '32-rank full run requires a qualified parity job'
    record=json.loads((root/'jobs'/parity/'parity.json').read_text())
    assert record['passed'] is True and record['library_job']==library
    assert build in record['jobs'], 'Parity does not qualify this smoke'
PY
fi
hours=1; [[ $mode == full ]] && hours=6
printf 'PLAN: %s %s, library=%s; %s distinct CPUs; original zero; strict12; %s hours\n' "$mode" "$key" "$library" "$ranks" "$hours"
[[ $action == apply ]] || exit 0
sbatch --parsable --partition=kshcnormal --cpus-per-task="$ranks" --time="$hours:00:00" \
 --chdir="$root" --job-name="rf-T-$mode-$key" --output="$root/logs/thermo-flame-%j.out" \
 --error="$root/logs/thermo-flame-%j.err" "$release/replication/development/temperature-inversion/job.sh" \
 "$root" "$release" "$library" "$ranks" "$key" "$mode" "$build"
