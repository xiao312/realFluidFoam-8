#!/usr/bin/env bash
set -euo pipefail
OUT=${1:?new build directory}; ARCHIVE=${2:?frozen source archive}; SOURCE=${3:?source commit}
OLD=/workspace/build/of8-direct-r3
[[ -n ${SLURM_JOB_ID:-} && ${WM_PROJECT_VERSION:-} == 8 && ! -e $OUT ]] || exit 2
printf '%s  %s\n' 3b0f1926a977f48701587cd323093d592dcb2a4020efd198e81ea72889d3d16d \
    "$OLD/lib/libcombustionModels.so" | sha256sum -c -
mkdir -p "$OUT/source" "$OUT/rf" "$OUT/bin" "$OUT/lib" "$OUT/logs"
tar -xf "$ARCHIVE" -C "$OUT/source"
cp "$OLD/lib/libcombustionModels.so" "$OUT/lib/"
for path in /opt/openfoam8/src/*; do
    name=${path##*/}; [[ $name == combustionModels ]] && continue
    ln -s "$path" "$OUT/rf/$name"
done
ln -s "$OUT/source/src/combustionModels" "$OUT/rf/combustionModels"
export LIB_rfFoam8_SRC="$OUT/rf" FOAM_USER_LIBBIN="$OUT/lib" FOAM_USER_APPBIN="$OUT/bin"
export WM_CXX="$(command -v g++)" CPATH="/usr/include/x86_64-linux-gnu${CPATH:+:$CPATH}"
export LD_LIBRARY_PATH="$OUT/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
[[ $(g++ -dumpfullversion) == 11.2.0 ]] || exit 3
wmakeLnInclude "$OUT/source/src/combustionModels" > "$OUT/logs/headers.log" 2>&1
node --input-type=module - "$OUT" "$SOURCE" <<'NODE'
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const [root, source] = process.argv.slice(2);
const path = `${root}/source/applications/solvers/reactingFoamSolveZ/Make/options`;
const before = readFileSync(path, 'utf8');
if ((before.match(/EXE_LIBS = /g) ?? []).length !== 1) throw new Error('Unexpected solver Make/options');
const after = before.replace('EXE_LIBS = ', 'EXE_LIBS = -B"/usr/lib/x86_64-linux-gnu/" -L"$(FOAM_LIBBIN)" ') +
  '\nLIB_PLATFORMS = $(FOAM_USER_LIBBIN)\n';
writeFileSync(path, after);
const hash = text => createHash('sha256').update(text).digest('hex');
writeFileSync(`${root}/build-options-patch.json`, JSON.stringify({ source, path,
  beforeSha256: hash(before), afterSha256: hash(after),
  change: 'Quoted GCC startup path and matching isolated custom-library lookup; no equation changes' }, null, 2) + '\n');
NODE
printf '#include <iostream>\nint main(){std::cout<<"GCC_LINK_RUN_OK\\n";}\n' > "$OUT/link-probe.C"
g++ -isystem /usr/include/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/ "$OUT/link-probe.C" -o "$OUT/link-probe"
"$OUT/link-probe"
if ! (cd "$OUT/source/applications/solvers/reactingFoamSolveZ" && wmake -j 2) > "$OUT/logs/solver.log" 2>&1; then
    tail -80 "$OUT/logs/solver.log"; exit 21
fi
ldd "$OUT/bin/reactingFoamSolveZ" > "$OUT/logs/ldd.txt"
if grep -F 'not found' "$OUT/logs/ldd.txt"; then exit 22; fi
grep -F "libcombustionModels.so => $OUT/lib/libcombustionModels.so" "$OUT/logs/ldd.txt"
grep -F 'libreactionThermophysicalModels.so => /opt/openfoam8/' "$OUT/logs/ldd.txt"
"$OUT/bin/reactingFoamSolveZ" -help > "$OUT/logs/help.txt" 2>&1
sha256sum "$OUT/bin/reactingFoamSolveZ" "$OUT/lib/libcombustionModels.so" > "$OUT/products.sha256"
printf 'source=%s\nlibrary_source=5af5cb92f0bd088a48df422fbe1084d1aec3240a\nlibrary_sha256=3b0f1926a977f48701587cd323093d592dcb2a4020efd198e81ea72889d3d16d\njob=%s\n' \
    "$SOURCE" "$SLURM_JOB_ID" > "$OUT/source-identity.txt"
