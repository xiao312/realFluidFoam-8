#!/bin/bash
set -eo pipefail
module load apps/apptainer/1.3.4
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
exec bash "$script_dir/run.sh" "$@"
