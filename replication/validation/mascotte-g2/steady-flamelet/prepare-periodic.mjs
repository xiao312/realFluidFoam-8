import {readFile,writeFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {loadSteadyTable} from './input.mjs';
import {realFluidInput} from '../direct-fgm/cold-input.mjs';
import {digest} from '../../fgm-of8/direct-verification/physical-input.mjs';

const [manifestPath,mode='--plan']=process.argv.slice(2);
if(!manifestPath||!['--plan','--apply'].includes(mode))throw Error('Use prepare-periodic.mjs INPUT.json [--plan|--apply]');
const m=JSON.parse(await readFile(manifestPath));
for(const key of Object.keys(m))if(!['table','metadata','thermo','out'].includes(key))throw Error(`Unknown input ${key}`);
for(const key of ['table','metadata','thermo','out'])if(typeof m[key]!=='string'||!m[key])throw Error(`Missing ${key}`);
const input=await loadSteadyTable(m.table,m.metadata),thermo=await realFluidInput(m.thermo,input);
if(thermo.record.equationOfState!=='soaveRedlichKwong')throw Error('This first qualification requires full SRK');
const cells=48,deltaT=2.5e-8,endTime=20*deltaT;
const states=Array.from({length:cells},(_,i)=>input.lookup(.2+.005*Math.sin(2*Math.PI*(i+.5)/cells)));
if(states.some(s=>s.temperature<thermo.record.effectiveInversionRange_K[0]||s.temperature>thermo.record.effectiveInversionRange_K[1]))throw Error('Profile outside executing thermo bounds');
const plan={schema:'steady-flamelet-periodic-v1',startTime:0,endTime,deltaT,cells,pressure:input.receipt.case.pressure_pa,
  fixedChi:input.chi,chiDefinition:input.chiDefinition,inputHashes:input.inputHashes,thermodynamics:thermo.record,
  initialZ:'0.2+0.005*sin(2*pi*(i+0.5)/48)',sourceTableOriginalSteadyConverged:input.receipt.original_steady_numerically_converged,
  transportedProgress:false,addedChemicalHeat:false,scientificAcceptance:false};
if(mode==='--plan'){console.log(JSON.stringify({dryRun:true,...plan},null,2));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Case construction requires an allocated qualification');
const out=resolve(m.out),here=dirname(fileURLToPath(import.meta.url));
const result=spawnSync(process.execPath,[resolve(here,'../../fgm-of8/direct-verification/prepare.mjs'),
  '--kind','contact','--cells',String(cells),'--delta-t',String(deltaT),'--out',out],{encoding:'utf8'});
if(result.status!==0)throw Error(result.stderr||result.stdout||'Base periodic construction failed');
const header=(name,cls='dictionary')=>`FoamFile { version 2.0; format ascii; class ${cls}; object "${name}"; }\n`;
async function field(name,dimensions,values){
  const data=Array.isArray(values)?`nonuniform List<scalar> ${values.length} ( ${values.join(' ')} )`:`uniform ${values}`;
  await writeFile(`${out}/0/${name}`,header(name,'volScalarField')+`dimensions [${dimensions}]; internalField ${data};
  boundaryField { left { type cyclic; } right { type cyclic; } transverse { type empty; } }\n`);
}
for(let s=0;s<input.metadata.species.length;s++)await field(input.metadata.species[s].name,'0 0 0 0 0 0 0',states.map(v=>v.y[s]));
for(const [name,dimensions,values] of [['Z','0 0 0 0 0 0 0',states.map(s=>s.z)],['c','0 0 0 0 0 0 0',states.map(s=>s.c)],
  ['T','0 0 0 1 0 0 0',states.map(s=>s.temperature)],['p','1 -1 -2 0 0 0 0',plan.pressure],['Ha','0 2 -2 0 0 0 0',0]])await field(name,dimensions,values);
await writeFile(`${out}/constant/thermophysicalProperties`,thermo.dictionary);
// The just-created analytic input is replaced completely; only this physical table is selected.
await writeFile(`${out}/constant/constant.tbl`,input.raw);
await writeFile(`${out}/constant/combustionProperties`,header('combustionProperties')+
  `combustionModel steadyFlamelet; steadyFlameletCoeffs { table "${out.replaceAll('\\','/')}/constant/constant.tbl"; fixedChi ${input.chi}; chiDefinition ${input.chiDefinition}; }\n`);
await writeFile(`${out}/constant/thermophysicalTransport`,header('thermophysicalTransport')+'laminar { model Fourier; }\n');
let control=await readFile(`${out}/system/controlDict`,'utf8');
control=control.replace(/endTime [^;]+;/,`endTime ${endTime};`).replace(/writeInterval [^;]+;/,'writeInterval 5;')
 .replace('fgmEnergyForm sensibleEnthalpy;','fgmEnergyForm absoluteEnthalpy;');
control+='fgmSkipUnusedDimix no; fgmProgressSourceEnabled no; fgmRequireHaInitialization yes; fgmSourceIntegration explicit;\nwriteFgmThermoClosure yes; fgmThermoClosureRelativeLimit 1e-8;\n';
await writeFile(`${out}/system/controlDict`,control);
const solution=await readFile(`${out}/system/fvSolution`,'utf8');
await writeFile(`${out}/system/fvSolution`,solution.replace('pRef 101325;',`pRef ${plan.pressure};`));
const hashes={};for(const name of ['constant/combustionProperties','constant/constant.tbl','constant/thermophysicalProperties','system/controlDict','system/fvSchemes','system/fvSolution',
 ...['Z','c','T','p','Ha','U',...input.metadata.species.map(s=>s.name)].map(n=>`0/${n}`)])hashes[name]=digest(await readFile(`${out}/${name}`));
await writeFile(`${out}/verification-input.json`,JSON.stringify({...plan,hashes},null,2)+'\n');
console.log(JSON.stringify({created:out,...plan}));
