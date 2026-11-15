import fs from 'node:fs';
import {createHash} from 'node:crypto';
const [root,action]=process.argv.slice(2),apply=action==='--apply';
if(!root?.startsWith('/workspace/cases/g2-relaxed-lowmach-s19-')||![undefined,'--apply'].includes(action))throw Error('Use owned fresh case [--apply]');
if(fs.readdirSync(root).some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0)))throw Error('Fresh undecomposed case required');
const manifest=JSON.parse(fs.readFileSync(root+'/direct-g2-input.json','utf8'));
if(manifest.startTime!==0||manifest.energyForm!=='absoluteEnthalpy'||manifest.pressure!==5610000)throw Error('Registered original-zero Cavalieri inputs required');
const file=root+'/system/controlDict',before=fs.readFileSync(file,'utf8');let after=before;
for(const flag of ['realFluidDensityTimeCorrection','realFluidDifferentialPressure']){
 const expression=new RegExp('\\b'+flag+' yes;','g');
 if([...after.matchAll(expression)].length!==1)throw Error('Expected one compressible flag:'+flag);
 after=after.replace(expression,flag+' no;');
}
if(/\brealFluidLowMachPressureSplit\s/.test(before))throw Error('Pressure model already configured');
after+='\nrealFluidLowMachPressureSplit yes;\nrealFluidThermodynamicPressure '+manifest.pressure+';\n';
const sha=b=>createHash('sha256').update(b).digest('hex');
const receipt={schema:'g2-lowmach-diagnostic/v1',CFDStartTime_s:0,p0_Pa:manifest.pressure,beforeSha256:sha(before),afterSha256:sha(after),modelChange:true,pressureModel:'Constant thermodynamic pressure;separate mechanical pressure',energyModel:'Thermal absolute Ha;kinetic/dynamic-pressure terms omitted',sourceAndTransport:'Unchanged exact10us relaxation, table, coefficients, mesh, boundaries, density predictor and Fourier transport',caloricAcceptanceChanged:false,scientificAcceptance:false};
if(apply){if(!process.env.SLURM_JOB_ID)throw Error('Slurm required');fs.writeFileSync(file,after);fs.writeFileSync(root+'/pressure-model-input.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});}
console.log(JSON.stringify({readOnly:!apply,...receipt},null,2));
