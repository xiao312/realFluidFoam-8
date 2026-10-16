#!/bin/bash
# Regression: sbatch executes a copy of job.sh outside the source directory.
set -euo pipefail
scratch_parent=${1:?Use an absolute test-output directory inside the local project}
test -d "$scratch_parent"
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
fixture=$(mktemp -d "$scratch_parent/dispatch-XXXXXX")
mkdir -p "$fixture/release/replication/environment" "$fixture/spool"
cp "$script_dir/job.sh" "$fixture/spool/job.sh"
printf '#!/bin/bash\nprintf "DISPATCH_OK\\n"\n' > "$fixture/release/replication/environment/run.sh"
module() { :; }
export -f module
bash "$fixture/spool/job.sh" "$fixture" unused-image "$fixture/release" preflight > "$fixture/result.txt"
grep -qx DISPATCH_OK "$fixture/result.txt"
echo "PASS: spool dispatch; retained fixture $fixture"
