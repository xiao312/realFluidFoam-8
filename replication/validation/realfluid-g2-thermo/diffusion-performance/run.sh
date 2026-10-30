#!/usr/bin/env bash
set -euo pipefail
paired=${1:?Usage: run.sh PAIRS_DIR PROBE [--apply]}
probe=${2:?Usage: run.sh PAIRS_DIR PROBE [--apply]}
mode=${3:---plan}
module=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
case "$mode" in --plan|--apply) ;; *) echo 'Expected --plan or --apply' >&2; exit 2;; esac
node -e 'const fs=require("fs"); const m=JSON.parse(fs.readFileSync(process.argv[1]+"/manifest.json")); if(m.schema!=="fgm-unused-diffusion-parity-v1")throw Error("Invalid manifest"); console.log(JSON.stringify({cases:m.pairs.map(x=>x.case),probe:process.argv[2]},null,2));' "$paired" "$probe"
if [[ "$mode" == --plan ]]; then exit 0; fi
: "${SLURM_JOB_ID:?Runtime qualification requires a FlamePilot Slurm allocation}"
[[ -x "$probe" ]] || { echo 'Qualified probe executable absent' >&2; exit 2; }
node -e 'const fs=require("fs"); const m=JSON.parse(fs.readFileSync(process.argv[1]+"/manifest.json")); for(const p of m.pairs){if(!/^[a-z-]+$/.test(p.case))throw Error("Bad case path"); console.log(p.case);}' "$paired" > "$paired/cases.txt"
sha256sum "$probe" > "$paired/executable.sha256"
ldd "$probe" > "$paired/executable.ldd"
while IFS= read -r case_name; do
  case_dir="$paired/$case_name"
  [[ ! -e "$case_dir/log.probe" ]] || { echo "Refuse rerun of $case_name" >&2; exit 2; }
  blockMesh -case "$case_dir" > "$case_dir/log.blockMesh" 2>&1
  "$probe" -case "$case_dir" > "$case_dir/log.probe" 2>&1
done < "$paired/cases.txt"
node "$module/compare.mjs" "$paired" > "$paired/log.compare"
node "$module/negative-controls.mjs" "$paired" "$probe" --apply > "$paired/log.negative-controls"
