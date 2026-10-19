#!/bin/bash
set -eo pipefail
root=${1:?}; release=${2:?}; mode=${3:?}; dependency=${4:-}
job="$root/jobs/$SLURM_JOB_ID"
module_path="$release/replication/development/solver-comparison"
if [[ $mode == deep-build ]]; then
 export MAMBA_ROOT_PREFIX="$job/mamba" CONDA_PKGS_DIRS="$job/cache/conda"
 tool="$root/cache/solver-comparison/micromamba-linux-64"
 printf '%s  %s\n' 9689782d863c05a1bf5d2d371ba527104e7a4eb4310c1637d8653b751aed9c82 "$tool" | sha256sum -c -
 "$tool" create -y --offline --no-rc -p "$job/cantera" -f "$root/cache/solver-comparison/dependencies-explicit.txt" > "$job/dependencies.log" 2>&1
 "$tool" list --no-rc -p "$job/cantera" --explicit > "$job/environment-explicit.txt"
 mkdir "$job/deepflame"
 tar -xzf "$root/cache/solver-comparison/deepflame-7cb3294.tar.gz" -C "$job/deepflame"
 build="$job"
else
 [[ $dependency =~ ^[0-9]+$ ]] || exit 2
 build="$root/jobs/$dependency"
 test -f "$build/deep-build-passed.txt"
fi
module load openfoam-v7-gcc9.3.0_openmpi4.1.5
# Redirect user outputs after the read-only module has selected the installed OF7.
export WM_PROJECT_USER_DIR="$job/openfoam-user"
export FOAM_USER_APPBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/bin"
export FOAM_USER_LIBBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/lib"
export FOAM_JOB_DIR="$job/jobControl" FOAM_RUN="$job/run"
export LD_LIBRARY_PATH="$build/cantera/lib:$LD_LIBRARY_PATH"
export WM_NCOMPPROCS="${SLURM_CPUS_PER_TASK:-8}"
mkdir -p "$FOAM_USER_APPBIN" "$FOAM_USER_LIBBIN" "$FOAM_JOB_DIR" "$FOAM_RUN"
cd "$build/deepflame"
if [[ $mode == deep-build ]]; then
 . ./configure.sh --libcantera_dir "$build/cantera" > "$job/configure.log" 2>&1
 . ./bashrc
 # Build all dependencies in upstream order; unrelated executable targets are omitted.
 sed '/wmake applications\/solvers\/dfHighSpeedFoam/,$d' Allwmake > "$job/deepflame/build-comparison.sh"
 bash ./build-comparison.sh -j "$SLURM_CPUS_PER_TASK" > "$job/build.log" 2>&1
 test -x "$DF_APPBIN/dfLowMachFoam"
 ldd "$DF_APPBIN/dfLowMachFoam" > "$job/solver-ldd.txt"
 ! grep -q 'not found' "$job/solver-ldd.txt"
 sha256sum "$DF_APPBIN/dfLowMachFoam" "$build/cantera/lib/libcantera.so" > "$job/solver-product.sha256"
 "$DF_APPBIN/dfLowMachFoam" -help > "$job/solver-help.txt" 2>&1
 printf '%s\n' 'CPU CVODE build and help passed; science unqualified' > "$job/deep-build-passed.txt"
else
 . ./bashrc
 cp "$build/solver-product.sha256" "$job/solver-product.sha256"
 sha256sum -c "$job/solver-product.sha256"
 python3 -B "$module_path/prepare.py" plan deep "$job/case" > "$job/case-plan.json"
 python3 -B "$module_path/prepare.py" apply deep "$job/case" > "$job/prepare.log"
 cp "$root/cache/solver-comparison/author-gri30.yaml" "$job/case/constant/author-gri30.yaml"
 blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
 decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
 cd "$job/case"
 mpirun --mca btl self,vader,tcp -np 8 "$DF_APPBIN/dfLowMachFoam" -parallel > "$job/solver.log" 2>&1
 grep -q '^End' "$job/solver.log"
fi
