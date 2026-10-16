#!/bin/bash
# Container entrypoint. No apt operations and no host MPI libraries are used.
set -eo pipefail
mode=${1:?mode}; release=${2:?source release}
job="/work/jobs/${RF_JOB_ID:?}"
[[ "$release" == /work/releases/* && -d "$release" ]] || exit 2
source /opt/openfoam8/etc/bashrc
[[ "$WM_PROJECT_VERSION" == 8 ]] || { echo 'Expected OpenFOAM Foundation 8' >&2; exit 2; }
export WM_PROJECT_USER_DIR="$job/openfoam-user"
export FOAM_USER_APPBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/bin"
export FOAM_USER_LIBBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/lib"
export PATH="$FOAM_USER_APPBIN:$PATH"
export LD_LIBRARY_PATH="$FOAM_USER_LIBBIN:$LD_LIBRARY_PATH"
export WM_NCOMPPROCS=${RF_CPUS:-2}
mkdir -p "$FOAM_USER_APPBIN" "$FOAM_USER_LIBBIN"
{
    date -u +%FT%TZ
    cat "$release/SOURCE_REVISION"
    uname -a
    printf 'OpenFOAM=%s\nWM_OPTIONS=%s\nHOME=%s\nTMPDIR=%s\n' "$WM_PROJECT_VERSION" "$WM_OPTIONS" "$HOME" "$TMPDIR"
    printf 'FOAM_USER_APPBIN=%s\nFOAM_USER_LIBBIN=%s\n' "$FOAM_USER_APPBIN" "$FOAM_USER_LIBBIN"
    g++ --version
    mpirun --version
    command -v wmake blockMesh
    test -f "$FOAM_SRC/finiteVolume/lnInclude/fvCFD.H"
    test -f "$FOAM_LIBBIN/libfiniteVolume.so"
    dpkg-query -W openfoam8 gcc g++ make libopenmpi-dev
} > "$job/environment.txt" 2>&1
blockMesh -help > "$job/blockMesh-help.txt" 2>&1
cat > "$job/tmp/mpi-check.cpp" <<'EOF'
#include <mpi.h>
#include <iostream>
int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank = 0, count = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &count);
    std::cout << "rank=" << rank << " size=" << count << std::endl;
    MPI_Finalize();
}
EOF
mpic++ "$job/tmp/mpi-check.cpp" -o "$job/tmp/mpi-check"
mpirun --mca btl self,vader,tcp -np 2 "$job/tmp/mpi-check" > "$job/mpi-check.txt" 2>&1
grep -q 'rank=0 size=2' "$job/mpi-check.txt"
grep -q 'rank=1 size=2' "$job/mpi-check.txt"
if [[ "$mode" == preflight ]]; then
    echo 'PASS: OF8 compiler, headers, tools and two-rank single-node MPI' | tee "$job/result.txt"
    exit 0
fi
[[ "$mode" == build ]] || exit 2
build="/work/builds/$RF_JOB_ID"
[[ ! -e "$build" ]] || { echo "Refusing to reuse build: $build" >&2; exit 2; }
mkdir "$build"
cp -a "$release/." "$build/"
# Upstream tracks generated objects. Remove them only from this new build copy.
find "$build/src" "$build/applications" -type d \( -name lnInclude -o -path '*/Make/linux*' \) -prune -exec rm -rf -- {} +
export LIB_rfFoam8_SRC="$build/src"
cd "$build"
bash ./Allwmake -j "$WM_NCOMPPROCS" > "$job/build.log" 2>&1
for name in realFluidFoam realFluidReactingFoam reactingFoam; do
    test -x "$FOAM_USER_APPBIN/$name"
    "$FOAM_USER_APPBIN/$name" -help > "$job/$name-help.txt" 2>&1
    ldd "$FOAM_USER_APPBIN/$name" > "$job/$name-ldd.txt"
    if grep -q 'not found' "$job/$name-ldd.txt"; then exit 1; fi
done
test -f "$FOAM_USER_LIBBIN/libspecie.so"
grep -F "$FOAM_USER_LIBBIN/libspecie.so" "$job/realFluidFoam-ldd.txt"
find "$FOAM_USER_APPBIN" "$FOAM_USER_LIBBIN" -type f -exec sha256sum {} + > "$job/products.sha256"
echo 'PASS: build, executable help, library resolution; scientific validation pending' | tee "$job/result.txt"
