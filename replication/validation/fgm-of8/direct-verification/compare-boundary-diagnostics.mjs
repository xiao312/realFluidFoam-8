import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const options={};
for(let i=2;i<process.argv.length;i+=2){
  const key=process.argv[i];
  if(!['--old','--new','--metadata','--out'].includes(key)||!process.argv[i+1]||options[key])
    throw Error('Use --old CASE --new CASE --metadata PHASE [--out NEW_JSON]');
  options[key]=resolve(process.argv[i+1]);
}
if(['--old','--new','--metadata'].some(k=>!options[k]))throw Error('Two original-zero cases and exact metadata required');
const hashes={},sha=b=>createHash('sha256').update(b).digest('hex');
async function text(path){const raw=await readFile(path);hashes[path]=sha(raw);return raw.toString();}
const metadata=JSON.parse(await text(options['--metadata']));
const roots=[options['--old'],options['--new']],manifests=[],times=[];
for(const root of roots){
  const m=JSON.parse(await text(root+'/verification-input.json'));manifests.push(m);
  if(m.startTime!==0||m.energyForm!=='absoluteEnthalpy'||m.tableKind!=='finite-rate-physical-table')
    throw Error('Original-zero physical-table absolute-Ha control required');
  const found=(await readdir(root)).filter(n=>Number.isFinite(Number(n))&&Number(n)>0)
    .sort((a,b)=>Number(a)-Number(b));
  const stamp=found.at(-1);
  if(!stamp||Math.abs(Number(stamp)-m.endTime)>Math.max(1e-15,m.endTime*1e-9))
    throw Error('Actual complete declared endpoint required');
  times.push(stamp);
}
if(manifests[0].endTime!==manifests[1].endTime||manifests[0].cells!==manifests[1].cells)
  throw Error('Different physical durations or meshes');
for(const relative of ['constant/constant.tbl','constant/thermophysicalProperties',
  ...[...metadata.speciesOrder,'p','T','Ha','U','Z','c'].map(n=>'0/'+n)]){
  const inputs=await Promise.all(roots.map(root=>text(root+'/'+relative)));
  if(inputs[0]!==inputs[1])throw Error('Different original input: '+relative);
}
function values(body,key,components,count){
  const many=new RegExp(key+'\\s+nonuniform\\s+List<(scalar|vector)>\\s+(\\d+)\\s*\\(([^]*?)\\)\\s*;').exec(body);
  if(many){
    const data=many[3].replace(/[()]/g,' ').trim().split(/\s+/).filter(Boolean).map(Number);
    if(Number(many[2])!==count||data.length!==count*components)throw Error('Wrong field shape');
    return data;
  }
  const one=new RegExp(key+'\\s+uniform\\s+([^;]+);').exec(body);
  if(!one)throw Error('Missing field value');
  const data=one[1].replace(/[()]/g,' ').trim().split(/\s+/).map(Number);
  if(data.length!==components)throw Error('Wrong uniform component count');
  return Array.from({length:count},()=>data).flat();
}
const rows=[],fields=[...metadata.speciesOrder,'rho','p','T','h','Ha','U','Z','c','fgmSc','fgmScSource','fgmQdot','fgmTdiag'];
let oldDiagnostic,newDiagnostic;
for(const name of fields){
  const raw=await Promise.all(roots.map((root,i)=>text(root+'/'+times[i]+'/'+name)));
  for(const s of raw)if(!new RegExp('object\\s+"?'+name+'"?\\s*;').test(s))throw Error('Field object differs: '+name);
  const [a,b]=raw.map(s=>values(s,'internalField',name==='U'?3:1,manifests[0].cells));
  if([...a,...b].some(v=>!Number.isFinite(v)))throw Error('Nonfinite internal field');
  const maximum=Math.max(...a.map((v,i)=>Math.abs(v-b[i]))),scale=Math.max(1,...a.map(Math.abs),...b.map(Math.abs));
  rows.push({field:name,relativeMaximum:maximum/scale,limit:1e-12,passed:maximum/scale<=1e-12});
  if(name==='fgmTdiag'){oldDiagnostic={raw:raw[0],internal:a[0]};newDiagnostic={raw:raw[1],internal:b[0]};}
}
const patches=[];
for(const name of ['left','right']){
  const blocks=[oldDiagnostic,newDiagnostic].map(d=>new RegExp('\\b'+name+'\\s*\\{([^{}]*)\\}').exec(d.raw)?.[1]);
  if(blocks.some(b=>!b))throw Error('Missing closed-control patch');
  const [oldValue,newValue]=blocks.map(b=>values(b,'value',1,1)[0]);
  const passed=Number.isFinite(newValue)&&newValue>0&&Math.abs(newValue/newDiagnostic.internal-1)<=1e-10;
  patches.push({patch:name,oldValue_K:oldValue,newValue_K:newValue,
    expectedHomogeneousTableTemperature_K:newDiagnostic.internal,oldStaleZero:oldValue===0,passed});
}
const report={schema:'fgm-calculated-boundary-parity/v1',CFDStart:0,physicalEnd_s:manifests[0].endTime,
  rows,patches,oldStaleZeroReproduced:patches.every(p=>p.oldStaleZero),
  passed:rows.every(r=>r.passed)&&patches.every(p=>p.passed&&p.oldStaleZero),
  inputHashes:hashes,scientificAcceptance:false};
if(options['--out'])await writeFile(options['--out'],JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(report,null,2));
if(!report.passed)process.exitCode=1;
