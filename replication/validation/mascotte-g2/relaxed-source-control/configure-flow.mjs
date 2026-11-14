import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {withInertSpecies} from './inert-species.mjs';
const [root,rawCr,action]=process.argv.slice(2),Cr=Number(rawCr),apply=action==='--apply';
if(!root||![1,100].includes(Cr)||![undefined,'--apply'].includes(action))throw Error('Use NEW_CASE 1|100 [--apply]');
if(fs.readdirSync(root).some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0))
  ||fs.existsSync(root+'/relaxed-flow-input.json'))throw Error('Fresh undecomposed factory case required');
const read=n=>fs.readFileSync(root+'/'+n,'utf8'),sha=b=>createHash('sha256').update(b).digest('hex');
const original=read('direct-g2-input.json'),factory=JSON.parse(original);
if(factory.startTime!==0||factory.closure!=='steady-flamelet'||factory.energyForm!=='absoluteEnthalpy'
  ||factory.initialization.config.mixtureFraction!==1)throw Error('Original-zero pure-fuel absolute-Ha factory case required');
const changes=[];
function change(name,after){const before=read(name);changes.push({name,before,after,beforeSha256:sha(before),afterSha256:sha(after)});}
const thermo=read('constant/thermophysicalProperties');
change('constant/thermophysicalProperties',withInertSpecies(thermo,'O2'));
change('constant/combustionProperties',`FoamFile {version 2.0;format ascii;class dictionary;object combustionProperties;}
combustionModel relaxedTable;relaxedTableCoeffs {table "${root}/constant/steady.tbl";relaxationSteps ${Cr};lookupRoundoffPolicy endpoint64epsilon;}
`);
let controls=read('system/controlDict');
if(!controls.includes('fgmEnergyForm absoluteEnthalpy;')||!controls.includes('fgmProgressSourceEnabled no;')
  ||!controls.includes('fgmRequireHaInitialization yes;'))throw Error('Absolute-Ha/source guards differ');
const additions={conserveTransportDensity:'yes',projectTabulatedZRoundoff:'yes',writeMixtureFractionBudget:'yes',writeFgmTiming:'yes',
  fgmThermoCorrectionPasses:'3',fgmIgnitionTime:'-1',realFluidDensityTimeCorrection:'yes',realFluidInnerThermoCorrectors:'yes',
  realFluidDifferentialPressure:'yes',realFluidPressureDensityConstraint:'enthalpy',realFluidPressureThermoRefresh:'yes'};
for(const[name,value]of Object.entries(additions)){
 if(new RegExp('\\b'+name+'\\s').test(controls))throw Error('Factory flag already set:'+name);
 controls+='\n'+name+' '+value+';\n';
}
change('system/controlDict',controls);
const record={schema:'relaxed-table-fresh-G2-input/v1',CFDStartTime_s:0,Cr,
  factoryManifestSha256:sha(original),unchangedTableSha256:sha(read('constant/steady.tbl')),
  closure:'Transport actual species; post-pure-mixing relaxation toward unchanged finite-chi table',
  targetIsPaperEquilibrium:false,sourceTau:'Cr*actual_dt; report actual adaptive timestep',
  inertBookkeeping:'O2; original thermo coefficients unchanged',speciesPredictorClipping:'Existing OF8 clipping retained and disclosed',
  energy:'Absolute Ha; chemical heat release diagnostic only, not added twice',
  changes:changes.map(({name,beforeSha256,afterSha256})=>({name,beforeSha256,afterSha256})),scientificAcceptance:false};
if(apply){
 if(!process.env.SLURM_JOB_ID)throw Error('Apply requires Slurm');
 for(const{name,after}of changes)fs.writeFileSync(root+'/'+name,after);
 fs.writeFileSync(root+'/relaxed-flow-input.json',JSON.stringify(record,null,2)+'\n',{flag:'wx'});
}
console.log(JSON.stringify({readOnly:!apply,...record},null,2));
