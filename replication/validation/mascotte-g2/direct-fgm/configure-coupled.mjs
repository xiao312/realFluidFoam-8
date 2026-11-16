import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';

const [directory,mode,action]=process.argv.slice(2);
if(!directory||!['inner','densityHa','densityHaDifferential'].includes(mode)||
   ![undefined,'--apply'].includes(action))
  throw Error('Use NEW_CASE inner|densityHa|densityHaDifferential [--apply]');
const root=resolve(directory),listing=await readdir(root);
if(listing.some(n=>/^processor/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0))||
   listing.includes('coupled-pressure-input.json')||listing.includes('cold-initialization-start.json'))
  throw Error('Fresh undecomposed, not-yet-initialized case required');
const manifestFile=`${root}/direct-g2-input.json`,manifestRaw=await readFile(manifestFile);
const manifest=JSON.parse(manifestRaw),file=`${root}/system/controlDict`;
const before=await readFile(file),text=before.toString(),solution=await readFile(`${root}/system/fvSolution`,'utf8');
if(manifest.startTime!==0||manifest.closure!=='fgm'||manifest.sourceIntegration!=='strangFixedState'||
   manifest.energyForm!=='absoluteEnthalpy'||manifest.thermodynamics?.mode!=='cold-real-fluid'||
   !/conserveTabulatedDensity\s+yes\s*;/.test(text)||
   !/realFluidPressureThermoRefresh\s+yes\s*;/.test(text)||
   !/writeFgmThermoClosure\s+yes\s*;/.test(text)||
   !/nCorrectors\s+(?:[2-9]|[1-9]\d+)\s*;/.test(solution))
  throw Error('Configured cold real-fluid split-FGM/Ha/conservative-density/audit case with >=2 pressure correctors required');
if(/\b(?:realFluidInnerThermoCorrectors|realFluidRhoHaPredictor|realFluidDifferentialPressure|realFluidLowMachPressureSplit|maxRhoHaPressureIterations)\b/.test(text))
  throw Error('Pressure coupling mode already selected; preserve it and create another case');
let after=text+'\nrealFluidInnerThermoCorrectors yes;\n';
if(mode!=='inner')after+='realFluidRhoHaPredictor yes;\nmaxRhoHaPressureIterations 6;\n';
if(mode==='densityHaDifferential')after+='realFluidDifferentialPressure yes;\nrealFluidPressureDensityConstraint enthalpy;\n';
const sha=b=>createHash('sha256').update(b).digest('hex');
const report={schema:'g2-split-fgm-pressure-iteration/v1',mode,startTime:0,CFD_steps:0,
  sourceLifecycle:'First half once per physical step; inner Euler re-solves from unchanged oldTime; second half recomputed from transport',
  densityHaPredictor:mode!=='inner',pressureTangent:mode==='densityHaDifferential'?'fixed-enthalpy SRK derivative':'existing psi product',
  maximumPressurePropertyIterations:mode==='inner'?1:6,
  beforeControlSha256:sha(before),afterControlSha256:sha(after),originalManifestSha256:sha(manifestRaw),
  acceptanceChanged:false,tableChanged:false,chemistryChanged:false,scientificAcceptance:false};
if(action!=='--apply'){console.log(JSON.stringify({readOnly:true,...report},null,2));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Apply requires an admitted allocation');
await writeFile(`${root}/coupled-pressure-input.json`,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
await writeFile(file,after);
manifest.coupledPressure=report;
await writeFile(manifestFile,JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({readOnly:false,...report},null,2));
