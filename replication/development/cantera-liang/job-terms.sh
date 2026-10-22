#!/bin/bash
# Term-level diagnostic for the stage-3 -> stage-4 step, plus both conductivity forms
# measured against the same screen.
#
# The blocking finding is that the model moves the flame speed the wrong way at case 4
# (+16.87 % where the paper moves -4.6 %). Two separable questions sit behind that:
#
#   1. *What does the implementation actually do to the conductivity term?* Answered at
#      fixed thermodynamic states by `model-probe`, which reports, for one converged
#      profile, the mixture-averaged conductivity (the stage-3 model), the full
#      Ely-Hanley conductivity (the stage-4 model) and the dense-increment form, at nine
#      temperatures and 1/100 atm. `probe_terms.py` reduces that table to the ratios the
#      step implies and compares them with the ratio the paper's step would need.
#   2. *Do the two conductivity forms differ on the flame grid?* Answered by the same
#      five-point stage-4 flame sweep run twice, once as `full` (the shipped model) and
#      once as `dense-increment`, reported against the same declared screen.
#
# Nothing here switches a variant because it lands closer to the paper: the sweep reports
# both forms, and the screen is the one the report already declares.
#
# Usage: job-terms.sh MODULE INPUTS RUN
#   INPUTS must contain the frozen case inputs, the converged stage-3 profile
#   (`profile-stage3-phi1.0.csv`), the attribution diagnostic and the sweep results that
#   the sensitivity is derived from.
set -euo pipefail

module=${1:?module directory}
inputs=${2:?inputs directory}
run=${3:?run directory}
build=$run/build
profile=$inputs/profile-stage3-phi1.0.csv
phis=${PHIS:-1.0,1.2,1.4}
per_run_timeout=${PER_RUN_TIMEOUT:-1200}
pass_budget=${PASS_WALL_BUDGET:-2600}

step=start
trap 'rc=$?; if [ "$rc" -ne 0 ]; then printf "FAILED step=%s rc=%s at %s\n" "$step" "$rc" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run/terms-status.txt"; fi' EXIT

mkdir -p "$run/probe"
printf 'terms start %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run/terms-status.txt"
printf 'phis=%s per_run_timeout=%s pass_budget=%s\n' \
    "$phis" "$per_run_timeout" "$pass_budget" >> "$run/terms-status.txt"

step=build
bash "$module/job-batch.sh" build "$module" "$inputs" "$build"
printf 'build done %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$run/terms-status.txt"

step=probe
# Fixed thermodynamic states, one converged profile: this measures the term, not the flame.
timeout --signal=TERM --kill-after=30 300 \
    "$build/model-probe" "$inputs" "$profile" "$run/probe/model-probe.csv"
printf 'probe done rows=%s %s\n' "$(wc -l < "$run/probe/model-probe.csv")" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$run/terms-status.txt"

step=reduce
python3 -B "$module/probe_terms.py" \
    --probe "$run/probe/model-probe.csv" \
    --attribution "$inputs/conductivity-attribution.json" \
    --results "$inputs/sweep-results.json" \
    --phi 0.95 --pressure-atm 100 --paper-step -0.046 \
    --out "$run/terms.json"
printf 'reduce done %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$run/terms-status.txt"

# The shipped form, on the same five-point grid the report screens. `full` is the default
# of job-sweep.sh, so this pass is the reference the dense increment is compared with.
step=sweep-full
VARIANT=full PER_RUN_TIMEOUT="$per_run_timeout" WALL_BUDGET="$pass_budget" \
    bash "$module/job-sweep.sh" "$module" "$inputs" "$run" "$build" 4 "$phis" \
    || printf 'sweep-full incomplete (see sweep.txt)\n' >> "$run/terms-status.txt"

step=sweep-dense
# Into a separate run directory so neither pass can claim the other's points, with its own
# copies of the frozen identities: job-sweep.sh verifies them per case.
mkdir -p "$run/dense"
cp "$run/module.sha256" "$run/dense/module.sha256"
cp "$run/inputs.sha256" "$run/dense/inputs.sha256"
VARIANT=dense-increment PER_RUN_TIMEOUT="$per_run_timeout" WALL_BUDGET="$pass_budget" \
    bash "$module/job-sweep.sh" "$module" "$inputs" "$run/dense" "$build" 4 "$phis" \
    || printf 'sweep-dense incomplete (see dense/sweep.txt)\n' >> "$run/terms-status.txt"

step=done
printf 'TERMS done %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$run/terms-status.txt"
printf 'terms done %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$run/terms.log"
tail -5 "$run/terms-status.txt" 2>/dev/null || true
