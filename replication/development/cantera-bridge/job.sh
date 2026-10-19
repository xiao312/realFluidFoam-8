#!/bin/bash
set -euo pipefail
root=${1:?}; release=${2:?}; sdk=${3:?}; inputs=${4:?}
[[ -n ${SLURM_JOB_ID:-} ]] || exit 2
for path in "$release" "$sdk" "$inputs"; do
 [[ $(realpath -e "$path") == "$root/"* ]] || exit 2
done
job=$root/jobs/$SLURM_JOB_ID
mkdir -p "$job"/{home,tmp,cache,config,apptainer}
export HOME=$job/home TMPDIR=$job/tmp XDG_CACHE_HOME=$job/cache OMP_NUM_THREADS=1
export LD_LIBRARY_PATH="$sdk/lib:${LD_LIBRARY_PATH:-}" CANTERA_DATA="$sdk/share/cantera/data"
export PKG_CONFIG_PATH="$sdk/lib/pkgconfig"
unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
cd "$job"
module_path=$release/replication/development/cantera-bridge
compiler=/public/software/compiler/gcc/11.2.0/bin/g++
flags=$($sdk/bin/pkg-config --cflags --libs cantera)
"$compiler" -std=c++17 -O2 -fPIC -shared -D_GLIBCXX_USE_CXX11_ABI=1 \
 "$module_path/bridge.cpp" $flags -Wl,-rpath,"$sdk/lib" -o librfcantera.so > compile.log 2>&1
"$compiler" -std=c++17 -O2 -D_GLIBCXX_USE_CXX11_ABI=0 \
 "$module_path/probe.cpp" -ldl -o bridge-probe > compile-probe.log 2>&1
sha256sum librfcantera.so bridge-probe > binary.sha256
ldd librfcantera.so > dependencies.txt
while read stage variant profile; do
 ./bridge-probe "$job/librfcantera.so" "$inputs" "$stage" "$variant" \
  "$root/jobs/$profile/result/profile.csv" > "check-$stage.txt"
done <<'CASES'
1 full 124919519
3 pressure-chemistry,smoothed-alpha 124939652
5 dense-increment,bounded-takahashi,pressure-chemistry 124937545
CASES
module load apps/apptainer/1.3.4
image=$root/images/openfoam8-rootfs-7d4e96e0b1a9
sha256sum -c "$image.source.sha256" > image-verified.txt
export APPTAINER_TMPDIR=$job/tmp APPTAINER_CACHEDIR=$root/cache/apptainer APPTAINER_CONFIGDIR=$job/config
unset APPTAINER_BIND APPTAINER_BINDPATH SINGULARITY_BIND SINGULARITY_BINDPATH
sdk_in=/work/${sdk#"$root/"};job_in=/work/jobs/$SLURM_JOB_ID
inputs_in=/work/${inputs#"$root/"}
apptainer exec --cleanenv --containall --underlay --no-eval --no-mount cwd,hostfs,bind-paths \
 --home "$job/home:/home/foam" --bind "$root:/work" --bind "$job/tmp:/tmp" \
 --workdir "$job/apptainer" --pwd "$job_in" "$image" /bin/bash -c '
 # OpenFOAM initialization probes optional shell tools and is not errexit-safe.
 . /opt/openfoam8/etc/bashrc
 set -euo pipefail
 test "$WM_PROJECT_VERSION" = 8
 test -f "$FOAM_LIBBIN/libOpenFOAM.so"
 export LD_LIBRARY_PATH="$1/lib:$LD_LIBRARY_PATH" CANTERA_DATA="$1/share/cantera/data"
 export LD_PRELOAD="$FOAM_LIBBIN/libOpenFOAM.so"
 ./bridge-probe "$2/librfcantera.so" "$3" 3 pressure-chemistry,smoothed-alpha /work/jobs/124939652/result/profile.csv
 ' bridge "$sdk_in" "$job_in" "$inputs_in" > container-check.txt 2>&1
cp "$release/SOURCE_REVISION" source-revision.txt
printf 'PASS: C ABI properties, sources and OF8-library coexistence; CFD not qualified\n' > result.txt
