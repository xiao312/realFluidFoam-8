#!/bin/bash
set -euo pipefail
action=${1:?}; root=${2:?}; release=${3:?}; sdk=${4:?}; inputs=${5:?}; stage=${6:?}; build=${7:-}
phi=${8:-1.10}
variant=${9:-full}
[[ $variant =~ ^(full|(dense-increment|bounded-takahashi|pressure-chemistry|fine-grid|smoothed-alpha|takahashi-table2|takahashi-high-t|takahashi-bulk|mass-gradient|total-enthalpy|pure-species-flux|soret|manual-soret)(,(dense-increment|bounded-takahashi|pressure-chemistry|fine-grid|smoothed-alpha|takahashi-table2|takahashi-high-t|takahashi-bulk|mass-gradient|total-enthalpy|pure-species-flux|soret|manual-soret))*)$ ]] || exit 2
pressure=${10:-100}
steady_rtol=${11:-1e-5}; steady_atol=${12:-1e-11}
[[ $pressure =~ ^[0-9]+([.][0-9]+)?$ ]] || exit 2
[[ $steady_rtol =~ ^[0-9.eE+-]+$ && $steady_atol =~ ^[0-9.eE+-]+$ ]] || exit 2
[[ $phi =~ ^[0-9]+([.][0-9]+)?$ ]] || exit 2
[[ $action == plan || $action == apply ]] || exit 2
root=$(realpath -e "$root")
for path in "$release" "$sdk" "$inputs"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
[[ $stage == build || $stage =~ ^[1-5]$ ]] || exit 2
if [[ $stage != build ]]; then
 [[ $(realpath -e "$build") == "$root/jobs/"* ]] || exit 2
 test -f "$build/build-passed.txt"
fi
printf 'Cantera stage=%s phi=%s variant=%s pressure_atm=%s rtol=%s atol=%s; 1 core; 3072 MiB; 4 hours; release=%s; sdk=%s; inputs=%s; build=%s\n' "$stage" "$phi" "$variant" "$pressure" "$steady_rtol" "$steady_atol" "$release" "$sdk" "$inputs" "$build"
[[ $action == apply ]] || exit 0
printf -v command '%q ' bash "$release/replication/development/cantera-liang/job.sh" "$root" "$release" "$sdk" "$inputs" "$stage" "${build:-none}" "$phi" "$variant" "$pressure" "$steady_rtol" "$steady_atol"
sbatch --parsable --partition=kshcnormal --job-name="rf-liang-$stage-$phi" --cpus-per-task=1 --mem=3072M --time=04:00:00 \
 --chdir="$root" --output="$root/logs/liang-$stage-%j.out" --error="$root/logs/liang-$stage-%j.err" \
 --wrap="$command"
