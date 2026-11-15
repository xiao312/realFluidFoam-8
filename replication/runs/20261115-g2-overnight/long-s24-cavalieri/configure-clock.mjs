import fs from 'node:fs';import crypto from 'node:crypto';
const[root,mode,action]=process.argv.slice(2),apply=action==='--apply',sha=x=>crypto.createHash('sha256').update(x).digest('hex');
if(!['steps','fixedTime'].includes(mode)||![undefined,'--apply'].includes(action)||fs.readdirSync(root).some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0)))throw Error('Fresh undecomposed case required');
const file=root+'/constant/combustionProperties',before=fs.readFileSync(file,'utf8');if(!before.includes('relaxationSteps 100;'))throw Error('Exact default required');
const after=mode==='steps'?before:before.replace('relaxationSteps 100;','relaxationMode fixedTimeExact;relaxationTime 1e-5;');
const receipt={mode,integration:'exactFrozenTarget',tau_s:mode==='fixedTime'?1e-5:null,defaultCr:mode==='steps'?100:null,startTime:0,beforeSha256:sha(before),afterSha256:sha(after),physicalChemistryRate:false,scientificAcceptance:false};
if(apply){if(!process.env.SLURM_JOB_ID)throw Error('Slurm required');fs.writeFileSync(file,after);fs.writeFileSync(root+'/source-clock-input.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});}console.log(JSON.stringify({readOnly:!apply,...receipt},null,2));
