#!/bin/bash
set -euo pipefail
release=${1:?}; job=${2:?}; source_id=${3:?}
[[ "$source_id" =~ ^[0-9]+$ ]] || exit 2
module="$release/replication/development/counterflow"
python3 -B "$module/continue.py" plan "/work/jobs/$source_id" "$job" > "$job/continuation-plan.json"
python3 -B "$module/continue.py" apply "/work/jobs/$source_id" "$job" > "$job/continuation-prepare.json"
named=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["source_executable"])' "$job/continuation.json")
sha256sum "$named" > "$job/solver-product.sha256"
ldd "$named" > "$job/named-solver-ldd.txt"
! grep -q 'not found' "$job/named-solver-ldd.txt"
grep -F '/work/jobs/124657926/openfoam-user/platforms/' "$job/named-solver-ldd.txt"
python3 -B "$module/steady_watch.py" "$job" "$named"
