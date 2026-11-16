import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const [directory,action]=process.argv.slice(2),apply=action==='--apply';
if(!directory||![undefined,'--apply'].includes(action))throw Error('Use FRESH_CASE [--apply]');
const root=resolve(directory),listing=await readdir(root);
if(listing.some(n=>/^processor/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0))||listing.includes('cold-initialization-start.json')||listing.includes('low-mach-input.json'))throw Error('Fresh undecomposed uninitialized case required');
const manifestPath=root+'/direct-g2-input.json',manifestRaw=await readFile(manifestPath),manifest=JSON.parse(manifestRaw);
if(manifest.startTime!==0||manifest.closure!=='fgm'||manifest.sourceIntegration!=='strangFixedState'||manifest.energyForm!=='absoluteEnthalpy'||manifest.thermodynamics?.mode!=='cold-real-fluid'||!(manifest.pressure>0)||manifest.coupledPressure?.mode!=='inner')throw Error('Explicit split-FGM/SRK/absolute-Ha inner-correction case required');
const controlPath=root+'/system/controlDict',solutionPath=root+'/system/fvSolution';
const controlRaw=await readFile(controlPath),solutionRaw=await readFile(solutionPath),control=controlRaw.toString(),solution=solutionRaw.toString();
if(/\b(?:realFluidRhoHaPredictor|realFluidDifferentialPressure|realFluidDensityTimeCorrection)\s+yes\s*;/.test(control)||/\brealFluidLowMachPressureSplit\b/.test(control)||/\bpMechanical(?:Final)?\s*\{/.test(solution))throw Error('Incompatible or already selected pressure model');
// The owned generator supplies one explicit regex group for p and pFinal.
const originalGroups=[...solution.matchAll(/"p\.\*"\s*\{([^{}]*)\}/g)];
if(originalGroups.length!==1)throw Error('Expected owned pressure solver pattern "p.*"');
const pressureGroups=['pMechanical','pMechanicalFinal'].map(name=>name+' {'+originalGroups[0][1]+'}');
const marker='\n}\nPIMPLE';if(solution.split(marker).length!==2)throw Error('Expected explicit solvers/PIMPLE boundary');
const nextSolution=solution.replace(marker,'\n'+pressureGroups.join('\n')+marker);
const nextControl=control+'\nrealFluidLowMachPressureSplit yes;\nrealFluidThermodynamicPressure '+manifest.pressure+';\n';
const sha=x=>createHash('sha256').update(x).digest('hex');
const report={schema:'genuine-fgm-low-mach-input/v1',startTime:0,CFD_steps:0,
 pressureModel:'constant EOS pressure; separately projected pMechanical',pressure_Pa:manifest.pressure,
 energyModel:'thermal absolute Ha; kinetic/dynamic-pressure-work terms omitted',
 equationApproximationChanged:true,sourceTableChanged:false,geometryChanged:false,acceptanceChanged:false,
 previousCompressibleFailuresRetained:true,earlierContactTestsReclassified:false,
 beforeControlSha256:sha(controlRaw),afterControlSha256:sha(nextControl),
 beforeSolutionSha256:sha(solutionRaw),afterSolutionSha256:sha(nextSolution),
 originalManifestSha256:sha(manifestRaw),scientificAcceptance:false};
if(apply){
 if(!process.env.SLURM_JOB_ID||!root.startsWith('/workspace/cases/'))throw Error('Apply only inside admitted project case');
 await writeFile(root+'/low-mach-input.json',JSON.stringify(report,null,2)+'\n',{flag:'wx'});
 await writeFile(controlPath,nextControl);await writeFile(solutionPath,nextSolution);
 manifest.lowMachModel=report;await writeFile(manifestPath,JSON.stringify(manifest,null,2)+'\n');
}
console.log(JSON.stringify({readOnly:!apply,...report},null,2));
