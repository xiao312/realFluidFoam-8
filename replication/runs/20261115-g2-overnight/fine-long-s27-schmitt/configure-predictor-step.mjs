import fs from 'node:fs';
import {createHash} from 'node:crypto';
const [root,action]=process.argv.slice(2),apply=action==='--apply';
if(!root||![undefined,'--apply'].includes(action))throw Error('Use NEW_CASE [--apply]');
if(fs.readdirSync(root).some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0))
  ||fs.existsSync(root+'/density-predictor-input.json'))throw Error('Fresh undecomposed original-zero case required');
const active=JSON.parse(fs.readFileSync(root+'/relaxed-flow-input.json','utf8'));
const file=root+'/system/controlDict',before=fs.readFileSync(file,'utf8');
if(active.CFDStartTime_s!==0||!before.includes('adjustTimeStep yes;')
  ||/\blimitDensityPredictorTimeStep\s/.test(before))throw Error('Original-zero adaptive case without prior predictor setting required');
const after=before+'\nlimitDensityPredictorTimeStep yes;\n';
const sha=b=>createHash('sha256').update(b).digest('hex');
const record={schema:'density-predictor-step-control/v1',CFDStartTime_s:0,
  beforeSha256:sha(before),afterSha256:sha(after),enabled:true,
  fieldValuesChanged:false,physicsOrAcceptanceChanged:false,
  method:'Source-free fixed-mesh Euler;dt<=0.9*rho/div(phi) where div(phi)>0',
  scientificAcceptance:false};
if(apply){
 if(!process.env.SLURM_JOB_ID)throw Error('Apply requires Slurm');
 fs.writeFileSync(file,after);fs.writeFileSync(root+'/density-predictor-input.json',JSON.stringify(record,null,2)+'\n',{flag:'wx'});
}
console.log(JSON.stringify({readOnly:!apply,...record},null,2));
