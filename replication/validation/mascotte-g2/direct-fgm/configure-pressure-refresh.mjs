import fs from 'node:fs';import crypto from 'node:crypto';
const[root,action]=process.argv.slice(2);if(!root||![undefined,'--apply'].includes(action))throw Error('Use NEW_CASE [--apply]');
if(fs.existsSync(root+'/cold-initialization.json')||fs.existsSync(root+'/cold-initialization-start.json')||fs.readdirSync(root).some(n=>/^processor\d+$/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0)))throw Error('Fresh not-yet-initialized case required');
const file=root+'/system/controlDict',before=fs.readFileSync(file,'utf8');if(before.includes('realFluidPressureThermoRefresh')||/realFluidColdEnergyProjection\s+yes/.test(before))throw Error('Unexpected experimental controls');
const after=before+'\nrealFluidPressureThermoRefresh yes;\n',sha=s=>crypto.createHash('sha256').update(s).digest('hex');
const receipt={startTime:0,beforeSHA256:sha(before),afterSHA256:sha(after),onlyPostPressurePropertyRefreshChanged:true,energyProjectionEnabled:false,readOnly:!action,scientificAcceptance:false};
if(action){if(!process.env.SLURM_JOB_ID)throw Error('Allocated preparation required');fs.writeFileSync(file,after);fs.writeFileSync(root+'/pressure-refresh-control.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});}console.log(JSON.stringify(receipt,null,2));
