#!/bin/bash
# Queue a bounded production allocation; no solver starts before smoke PASS.
set -Eeuo pipefail
action=${1:?}; root=${2:?}; image=${3:?}; release=${4:?}; key=${5:?}; smoke=${6:?}
[[ "$action" == plan || "$action" == apply ]] || exit 2
[[ "$key" == phi110-cool1400 || "$key" == phi110-equilibrium ]] || exit 2
[[ "$smoke" =~ ^[0-9]+$ ]] || exit 2
bash "$release/replication/environment/workspace.sh" plan "$root" >/dev/null
for path in "$root" "$image" "$release"; do
    [[ "$path" =~ ^/[a-zA-Z0-9_./-]+$ && $(realpath -e "$path") == "$path" ]] || exit 2
done
[[ "$image" == "$root/"* && "$release" == "$root/"* ]] || exit 2
sha=$(cat "$release/SOURCE_REVISION")
[[ "$sha" =~ ^[a-f0-9]{40}$ ]] || exit 2
grep -Fx "source=$sha" "$root/jobs/$smoke/validation-inputs.txt"
grep -Fx "stage=paper-premixed-$key-smoke" "$root/jobs/$smoke/validation-inputs.txt"
state=$(sacct -j "$smoke" -n -X -o State | tr -d ' ' | head -n 1)
[[ "$state" == RUNNING || "$state" == COMPLETED ]] || {
    echo "Expected running/completed smoke; found $state" >&2; exit 2;
}
# Restrict path/selector characters above so this POSIX shell wrapper is literal.
guard="grep -Fx 'PASS: paper premixed $key smoke; convergence remains unqualified' '$root/jobs/$smoke/result.txt' && grep -Fx 'source=$sha' '$root/jobs/$smoke/validation-inputs.txt' && bash '$release/replication/environment/job.sh' '$root' '$image' '$release' validation 124657926 'paper-premixed-$key-full'"
args=(--parsable --partition=kshcnormal --nodes=1 --ntasks=1 --cpus-per-task=8 --time=1440
    --dependency="afterok:$smoke" --kill-on-invalid-dep=yes
    --job-name="rfpaper-$key-full" --chdir="$root"
    --output="$root/logs/%x-%j.out" --error="$root/logs/%x-%j.err" --wrap="$guard")
printf 'Conditional production: source=%s key=%s smoke=%s reservation=192-core-hours\n' "$sha" "$key" "$smoke"
printf 'sbatch '; printf '%q ' "${args[@]}"; printf '\n'
if [[ "$action" == apply ]]; then
    ledger="$root/results/paper-premixed-reservations.tsv"
    exec 9>"$ledger.lock"; flock -x 9
    if grep -q "$(printf '\t%s\t%s$' "$key-full" "$sha")" "$ledger"; then
        echo 'Submission already recorded; inspect ledger before retrying' >&2; exit 2
    fi
    id=$(sbatch "${args[@]}")
    printf '%s\t192\t%s\t%s\n' "$id" "$key-full" "$sha" >> "$ledger"
    echo "SUBMITTED $id; dependency afterok:$smoke"
fi
