#!/usr/bin/env bash
set -euo pipefail
OUT=${1:?new build}; ARCHIVE=${2:?frozen archive}; SOURCE=${3:?source commit}; FULL=${4:?complete full build}
[[ -n ${SLURM_JOB_ID:-} && ${WM_PROJECT_VERSION:-} == 8 && ! -e $OUT ]] || exit 2
node --input-type=module - "$FULL" <<'NODE'
import {readFileSync} from 'node:fs'; import {createHash} from 'node:crypto';
const root=process.argv[2], receipt=JSON.parse(readFileSync(`${root}/build-qualification.json`));
const products=receipt.products.filter(p=>/^lib\/lib[^/]+\.so$/.test(p.file));
if(!receipt.compile_link_help_passed || receipt.custom_library_count!==15 || products.length!==15) throw Error('Incomplete full build');
for(const p of products){const raw=readFileSync(`${root}/${p.file}`);if(raw.length!==p.bytes || createHash('sha256').update(raw).digest('hex')!==p.sha256) throw Error(`Changed full library ${p.file}`);}
NODE
mkdir -p "$OUT/source" "$OUT/bin" "$OUT/logs"
tar -xf "$ARCHIVE" -C "$OUT/source"
export LIB_rfFoam8_SRC="$FULL/source/src" FOAM_USER_LIBBIN="$FULL/lib" FOAM_USER_APPBIN="$OUT/bin"
export WM_CXX="$(command -v g++)" CPATH="/usr/include/x86_64-linux-gnu${CPATH:+:$CPATH}"
export LD_LIBRARY_PATH="$FULL/lib:/opt/gcc-11.2.0/lib64:${LD_LIBRARY_PATH:-}"
[[ $(g++ -dumpfullversion) == 11.2.0 ]] || exit 3
node --input-type=module - "$OUT" "$SOURCE" <<'NODE'
import{readFileSync,writeFileSync}from'node:fs';import{createHash}from'node:crypto';
const[root,source]=process.argv.slice(2),records=[];
for(const module of ['applications/solvers/reactingFoamSolveZ','replication/validation/realfluid-g2-thermo/probe']){
 const file=`${root}/source/${module}/Make/options`, before=readFileSync(file,'utf8');
 if((before.match(/EXE_LIBS = /g)??[]).length!==1)throw Error(`Unexpected ${file}`);
 const after=before.replace('EXE_LIBS = ','EXE_LIBS = -B"/usr/lib/x86_64-linux-gnu/" -L"$(FOAM_USER_LIBBIN)" -L"$(FOAM_LIBBIN)" ');
 writeFileSync(file,after);const hash=s=>createHash('sha256').update(s).digest('hex');
 records.push({file:module+'/Make/options',beforeSha256:hash(before),afterSha256:hash(after)});
}
writeFileSync(`${root}/build-adjustments.json`,JSON.stringify({source,change:'Quoted startup path and full custom library search first; no equation changes',records},null,2)+'\n');
NODE
printf '#include <iostream>\nint main(){std::cout<<"FULL_GCC_LINK_RUN_OK\\n";}\n' > "$OUT/link-probe.C"
g++ -isystem /usr/include/x86_64-linux-gnu -B/usr/lib/x86_64-linux-gnu/ "$OUT/link-probe.C" -o "$OUT/link-probe"
"$OUT/link-probe"
for module in applications/solvers/reactingFoamSolveZ replication/validation/realfluid-g2-thermo/probe; do
    name=${module##*/}
    if ! (cd "$OUT/source/$module" && wmake -j 2) > "$OUT/logs/$name-build.log" 2>&1; then tail -80 "$OUT/logs/$name-build.log"; exit 20; fi
done
for binary in reactingFoamSolveZ realFluidG2ThermoProbe; do
    ldd "$OUT/bin/$binary" > "$OUT/logs/$binary-ldd.txt"
    if grep -F 'not found' "$OUT/logs/$binary-ldd.txt"; then exit 21; fi
    "$OUT/bin/$binary" -help > "$OUT/logs/$binary-help.txt" 2>&1
done
sha256sum "$OUT/bin/reactingFoamSolveZ" "$OUT/bin/realFluidG2ThermoProbe" "$FULL/build-qualification.json" > "$OUT/products.sha256"
printf 'executable_source=%s\nfull_library_build=%s\njob=%s\n' "$SOURCE" "$FULL" "$SLURM_JOB_ID" > "$OUT/source-identity.txt"
