#!/bin/bash
set -eo pipefail
module load apps/apptainer/1.3.4
script_dir="${3:?source release}/replication/environment"
exec bash "$script_dir/run.sh" "$@"
