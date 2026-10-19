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
 printf '%s  %s\n' 7f114d8ccac2753ab8c31db47dcfaa1204662db6d27f21b24122bd6539ada559 "$root/cache/solver-comparison/deepflame-7cb3294.tar.gz" | sha256sum -c -
 tar -xzf "$root/cache/solver-comparison/deepflame-7cb3294.tar.gz" -C "$job/deepflame"
 # The pinned upstream stores CRLF shell files. Normalize only the build copy.
 python3 - "$job/deepflame" <<'PY'
from pathlib import Path
import sys
for p in Path(sys.argv[1]).rglob('*'):
    if p.is_file() and (p.suffix in ('.sh', '.in') or p.name.startswith('Allw')):
        data=p.read_bytes()
        if b'\r\n' in data:p.write_bytes(data.replace(b'\r\n',b'\n'))
PY
 python3 -B "$module_path/source_audit.py" "$root/cache/solver-comparison/deepflame-7cb3294.tar.gz" "$job/deepflame" > "$job/source-audit.json"
 build="$job"
else
 [[ $dependency =~ ^[0-9]+$ ]] || exit 2
 build="$root/jobs/$dependency"
 test -f "$build/deep-build-passed.txt"
fi
module load openfoam-v7-gcc9.3.0_openmpi4.1.5
# The site module leaves the default HPC-X mpicc on PATH. Select the MPI that
# supplies the installed OF7 libPstream dependency, for both headers and runtime.
export MPI_ARCH_PATH=/public/software/mpi/openmpi/openmpi-4.1.5
test -x "$MPI_ARCH_PATH/bin/mpirun"
unset OPAL_PREFIX
export PATH="$MPI_ARCH_PATH/bin:$PATH"
export LD_LIBRARY_PATH="$MPI_ARCH_PATH/lib:$LD_LIBRARY_PATH"
mpirun --version > "$job/mpi-version.txt"
mpicc --showme > "$job/mpi-wrapper.txt"
# Redirect user outputs after the read-only module has selected the installed OF7.
export WM_PROJECT_USER_DIR="$job/openfoam-user"
export FOAM_USER_APPBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/bin"
export FOAM_USER_LIBBIN="$WM_PROJECT_USER_DIR/platforms/$WM_OPTIONS/lib"
export FOAM_JOB_DIR="$job/jobControl" FOAM_RUN="$job/run"
export LD_LIBRARY_PATH="$build/cantera/lib:$LD_LIBRARY_PATH"
export WM_NCOMPPROCS="${SLURM_CPUS_PER_TASK:-8}"
mkdir -p "$FOAM_USER_APPBIN" "$FOAM_USER_LIBBIN" "$FOAM_JOB_DIR" "$FOAM_RUN"
# This installed OF7 and the locked Cantera both export the C++11 string ABI.
# SCNet's default devtoolset compiler instead defaults to ABI=0; make it explicit.
unset CPLUS_INCLUDE_PATH C_INCLUDE_PATH CPATH LIBRARY_PATH
compiler=/public/software/compiler/gcc/11.2.0/bin/g++
test -x "$compiler"
mkdir -p "$job/compiler"
cat > "$job/compiler/g++" <<EOF
#!/bin/sh
link=yes
for arg in "\$@"; do
 case "\$arg" in -c|-E|-S|--version) link=no ;; esac
done
if [ "\$link" = yes ]; then
 exec "$compiler" -D_GLIBCXX_USE_CXX11_ABI=1 "\$@" -L"$MPI_ARCH_PATH/lib" -Wl,-rpath-link,"$MPI_ARCH_PATH/lib" -lmpi
fi
exec "$compiler" -D_GLIBCXX_USE_CXX11_ABI=1 "\$@"
EOF
chmod +x "$job/compiler/g++"
export PATH="$job/compiler:$PATH"
g++ --version > "$job/compiler-version.txt"
g++ -dM -E -x c++ -include string /dev/null | grep _GLIBCXX_USE_CXX11_ABI > "$job/compiler-abi.txt"
grep -q '_GLIBCXX_USE_CXX11_ABI 1' "$job/compiler-abi.txt"
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
 python3 - "$job/case/constant/author-gri30.yaml" <<'PY'
from pathlib import Path
import sys, hashlib, json
p=Path(sys.argv[1]); original=p.read_bytes()
text=original.decode().replace('kinetics: bulk','kinetics: gas').replace('transport: mixture-averaged','transport: Mix')
text=text.replace('name: ""','name: gas').replace('T: 1.0e-03','T: 298.0')
p.write_text(text)
p.with_suffix('.compatibility.json').write_text(json.dumps({
    'original_sha256':hashlib.sha256(original).hexdigest(),
    'compatible_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
    'changes':'Cantera 2.6 type names and unused default phase state; coefficients unchanged'},indent=2))
PY
 g++ -std=c++14 -I"$build/cantera/include" "$module_path/mechanismCheck.C" \
  -L"$build/cantera/lib" -lcantera -o "$job/mechanism-check" > "$job/mechanism-check-build.log" 2>&1
 "$job/mechanism-check" "$job/case/constant/author-gri30.yaml" > "$job/mechanism-check.txt" 2>&1
 blockMesh -case "$job/case" > "$job/blockMesh.log" 2>&1
 decomposePar -case "$job/case" > "$job/decompose.log" 2>&1
 cd "$job/case"
 mpirun --mca btl self,vader,tcp -np 8 "$DF_APPBIN/dfLowMachFoam" -parallel > "$job/solver.log" 2>&1
 grep -q '^End' "$job/solver.log"
fi
