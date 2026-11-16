import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const [directory,action]=process.argv.slice(2),apply=action==='--apply';
if(!directory||![undefined,'--apply'].includes(action))throw Error('Use CASE [--apply]');
const root=resolve(directory),sha=b=>createHash('sha256').update(b).digest('hex');
const manifestBytes=await readFile(root+'/direct-g2-input.json'),manifest=JSON.parse(manifestBytes);
const names=await readdir(root);
if(manifest.startTime!==0||manifest.closure!=='fgm'||!manifest.ransDiagnostic||
  manifest.algebraicSgs||manifest.skipUnusedDiffusion!==false||
  names.some(n=>n.startsWith('processor')||n.startsWith('cold-initialization')||
    (Number.isFinite(Number(n))&&Number(n)>0)))throw Error('Fresh full-property RANS FGM preparation required');
const paths=['constant/momentumTransport','constant/thermophysicalTransport','system/controlDict'];
const before=Object.fromEntries(await Promise.all(paths.map(async p=>[p,await readFile(root+'/'+p,'utf8')])));
if(!/model\s+kEpsilon\s*;/.test(before[paths[0]])||!/simulationType\s+RAS\s*;/.test(before[paths[0]]))
  throw Error('Unexpected model or diffusion policy');
const after={...before};
after[paths[0]]=before[paths[0]].replace(/simulationType\s+RAS\s*;/,'simulationType LES;')
  .replace(/RAS\s*\{[^{}]*\}/,'LES { model Smagorinsky; delta cubeRootVol; turbulence on; printCoeffs on; }');
after[paths[1]]=before[paths[1]].replace(/RAS\s*\{\s*model\s+eddyDiffusivity\s*;\s*Prt\s+0\.7\s*;\s*\}/,
  'LES { model eddyDiffusivity; Prt 0.85; }');
if(after[paths[1]]===before[paths[1]])throw Error('Unexpected original thermal transport');
after[paths[2]]=before[paths[2]].replace('fields (k epsilon nut alphat);','fields (nut alphat);');
const report={schema:'g2-algebraic-sgs/v1',CFDStart:0,model:'Smagorinsky',
  delta:'cubeRootVol',Prt:0.85,Sct:0.85,coefficients:'Stock OF8 defaults; no fit',
  paperDifferences:['Axisymmetric wedge, not 3D LES','Static rather than dynamic Smagorinsky',
    'No PDF or variance','Shared unity-Le diffusion implies Sct0.85, paper0.7'],
  retainedUnusedInitialFields:['k','epsilon'],sourceChanged:false,acceptanceChanged:false,
  scientificAcceptance:false,baselineManifestSha256:sha(manifestBytes),
  changes:paths.map(p=>({path:p,beforeSha256:sha(before[p]),afterSha256:sha(after[p])}))};
manifest.ransDiagnosticBaseline=manifest.ransDiagnostic;
delete manifest.ransDiagnostic;
manifest.algebraicSgs=report;
manifest.approximations=manifest.approximations.filter(s=>!s.includes('RANS kEpsilon')&&!s.includes('Prt=Sct=0.7'));
manifest.approximations.push(...report.paperDifferences,'Algebraic SGS isolation diagnostic; no statistical LES qualification');
if(apply){
  if(!process.env.SLURM_JOB_ID||!root.startsWith('/workspace/cases/'))throw Error('Admitted project case required');
  await writeFile(root+'/algebraic-sgs.json',JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  for(const p of paths)await writeFile(root+'/'+p,after[p]);
  await writeFile(root+'/direct-g2-input.json',JSON.stringify(manifest,null,2)+'\n');
}
console.log(JSON.stringify({readOnly:!apply,...report},null,2));
