import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { scalarValues } from '../diagnostics.mjs';
const [serial,parallel,n,c,output]=process.argv.slice(2), ranks=Number(n),cells=Number(c);
if(!serial||!parallel||!output||!Number.isInteger(ranks)||ranks<2||!Number.isInteger(cells)||cells<ranks)throw new Error('Use check-initialization-parity.mjs SERIAL PARALLEL RANKS CELLS OUTPUT');
const leftRaw=await readFile(`${serial}/0/Ha`),rightRaw=await readFile(`${parallel}/0/Ha`);
const left=scalarValues(leftRaw.toString(),'Ha'),right=scalarValues(rightRaw.toString(),'Ha');
for(const values of [left,right])if(![1,cells].includes(values.length)||!values.every(Number.isFinite))throw new Error('Invalid finite initialized Ha field');
let maximumAbsoluteError=0,scale=1;
for(let i=0;i<cells;i++){
 const a=left[left.length===1?0:i],b=right[right.length===1?0:i];
 maximumAbsoluteError=Math.max(maximumAbsoluteError,Math.abs(a-b));scale=Math.max(scale,Math.abs(a));
}
const a=JSON.parse(await readFile(`${serial}/cold-initialization.json`)),b=JSON.parse(await readFile(`${parallel}/cold-initialization.json`));
if(!a.initialized||!b.initialized||a.ranks!==1||b.ranks!==ranks||b.rankOutputs.length!==ranks||
 a.thermoDictionarySha256!==b.thermoDictionarySha256||a.binaries.probe.sha256!==b.binaries.probe.sha256)throw new Error('Initialization receipt or executable identity mismatch');
const relativeError=maximumAbsoluteError/scale,limit=1e-12;
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const report={schema:'full-runtime-initialization-parity/v1',serial,parallel,ranks,cells,maximumAbsoluteError_J_kg:maximumAbsoluteError,
 relativeError,limit,allRankMarkersVerified:true,serialHaSha256:hash(leftRaw),parallelHaSha256:hash(rightRaw),
 probeSha256:a.binaries.probe.sha256,thermoDictionarySha256:a.thermoDictionarySha256,
 status:relativeError<=limit?'pass':'fail',physicalFlameValidation:false};
await writeFile(output,JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report,null,2));
if(report.status!=='pass')process.exitCode=1;
