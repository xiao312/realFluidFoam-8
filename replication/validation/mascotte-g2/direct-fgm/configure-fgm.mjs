import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const [directory,...args]=process.argv.slice(2),options={};
if(!directory)throw Error('Use NEW_CASE [--ignition-time SECONDS] [--apply]');
for(let i=0;i<args.length;i++) {
  if(args[i]==='--apply')options.apply=true;
  else if(args[i]==='--ignition-time'&&args[i+1])options.ignition=Number(args[++i]);
  else throw Error(`Unknown/missing option ${args[i]}`);
}
const root=resolve(directory),input=JSON.parse(await readFile(`${root}/direct-g2-input.json`));
if(input.startTime!==0||input.closure!=='fgm'||input.sourceIntegration!=='strangFixedState'||input.energyForm!=='absoluteEnthalpy'||
   (await readdir(root)).some(n=>n.startsWith('processor')||(Number.isFinite(Number(n))&&Number(n)>0)))
  throw Error('Fresh undecomposed split-FGM absolute-Ha case required');
if(options.ignition!==undefined&&(!Number.isFinite(options.ignition)||options.ignition<0||options.ignition>=input.endTime))
  throw Error('Ignition must be finite and precede the requested endpoint');
const controlPath=`${root}/system/controlDict`,solutionPath=`${root}/system/fvSolution`;
const beforeControl=await readFile(controlPath),beforeSolution=await readFile(solutionPath);
if(/conserveTabulatedDensity|fgmThermoCorrectionPasses|fgmIgnitionTime/.test(beforeControl))throw Error('Controls already configured');
let control=beforeControl.toString()+
  '\nconserveTabulatedDensity yes;\nfgmThermoCorrectionPasses 3;\nwriteMixtureFractionBudget yes;\nwriteFgmTiming yes;\n';
if(input.thermodynamics.mode==='cold-real-fluid')control+='realFluidPressureThermoRefresh yes;\n';
if(options.ignition!==undefined)control+=`fgmIgnitionTime ${options.ignition};
fgmIgnitionTable "${root.replaceAll('\\','/')}/constant/physical.tbl";
fgmIgnitionAxialLength 0.004; fgmIgnitionZMin 0.1; fgmIgnitionZMax 0.3;
fgmIgnitionMode sourcePeak; fgmIgnitionNumericalReset yes; fgmIgnitionDeltaT 1e-7;\n`;
const entries=['Z','ZFinal','c','cFinal'].map(n=>
  `${n} { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-12; relTol 0; }`).join('\n');
if(!beforeSolution.toString().includes('\n}\nPIMPLE'))throw Error('Expected fresh generated solver dictionary');
const solution=beforeSolution.toString().replace('\n}\nPIMPLE',`\n${entries}\n}\nPIMPLE`);
const sha=b=>createHash('sha256').update(b).digest('hex');
const report={schema:'g2-physical-fgm-controls/v1',startTime:0,CFD_steps:0,
  ignition_time_s:options.ignition??null,ignition_region:options.ignition===undefined?null:{x_m:[0,.004],Z:[.1,.3]},
  source:'Signed physical tabulated raw-C source; no arbitrary relaxation timescale',
  control_before_sha256:sha(beforeControl),control_after_sha256:sha(control),
  solution_before_sha256:sha(beforeSolution),solution_after_sha256:sha(solution),
  acceptance_limits_changed:false,scientific_acceptance:false};
if(options.apply){
  if(!process.env.SLURM_JOB_ID)throw Error('Apply requires the admitted allocation');
  await writeFile(`${root}/fgm-controls.json`,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  await writeFile(controlPath,control);await writeFile(solutionPath,solution);
}
console.log(JSON.stringify({readOnly:!options.apply,...report},null,2));
