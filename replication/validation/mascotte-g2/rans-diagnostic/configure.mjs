import { readFile, writeFile, readdir, mkdir } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { createHash } from 'node:crypto';

const [casePath, configPath, action] = process.argv.slice(2);
if (!casePath || !configPath || (action !== undefined && action !== '--apply'))
  throw Error('Use CASE CONFIG.json [--apply]; default is read-only');
const root=resolve(casePath), hash=b=>createHash('sha256').update(b).digest('hex');
const configRaw=await readFile(resolve(configPath)), config=JSON.parse(configRaw);
const keys=(v,allowed,label)=>{
  if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).some(k=>!allowed.includes(k)))
    throw Error(`Unknown or invalid ${label} fields`);
};
keys(config,['schema','model','transport','Prt','inlets','initial','provenance'],'configuration');
keys(config.inlets,['loxinlet','ch4inlet'],'inlets');
keys(config.initial,['k_m2_s2','length_m'],'initial');
if (config.schema!=='g2-rans-diagnostic/v1' || config.model!=='kEpsilon' ||
    config.transport!=='eddyDiffusivity' || config.Prt!==0.7 || !config.provenance)
  throw Error('Explicit kEpsilon/eddyDiffusivity Prt0.7 diagnostic required');
const finite=(x,lo,hi,label)=>{if(!Number.isFinite(x)||x<=lo||x>hi)throw Error(`Invalid ${label}`);};
for(const name of ['loxinlet','ch4inlet']){
  keys(config.inlets[name],['intensity','length_m'],name);
  finite(config.inlets?.[name]?.intensity,0,0.2,`${name}.intensity`);
  finite(config.inlets[name].length_m,0,0.05,`${name}.length_m`);
}
finite(config.initial?.k_m2_s2,0,100,'initial k');
finite(config.initial.length_m,0,0.05,'initial length');
const names=await readdir(root);
if(!names.includes('0') || names.some(n=>/^processor/.test(n)||
    (Number.isFinite(Number(n))&&Number(n)>0)) || names.includes('rans-diagnostic.json') ||
    names.includes('cold-initialization-start.json'))throw Error('New undecomposed, uninitialized time-zero case required');
const manifestRaw=await readFile(`${root}/direct-g2-input.json`), m=JSON.parse(manifestRaw);
if(m.startTime!==0 || m.closure!=='steady-flamelet' || m.energyForm!=='absoluteEnthalpy' ||
   m.thermodynamics?.mode!=='cold-real-fluid' || m.pressure!==5610000 ||
   m.initialization?.config?.mode!=='uniform-steady' ||
   m.streams?.loxinlet?.temperature!==85 || m.streams?.ch4inlet?.temperature!==288)
  throw Error('Registered cold steady-table G2 case required');
const original={}, changed={};
async function read(name){const b=await readFile(`${root}/${name}`);original[name]=b;return b.toString();}
const once=(text,pattern,replacement,label)=>{
  if([...text.matchAll(new RegExp(pattern.source,'g'))].length!==1)throw Error(`Unexpected ${label}`);
  return text.replace(pattern,replacement);
};
const momentum=await read('constant/momentumTransport');
changed['constant/momentumTransport']=once(momentum,/simulationType\s+laminar\s*;/,
  'simulationType RAS;\nRAS { model kEpsilon; turbulence on; printCoeffs on; }','momentum selection');
const transport=await read('constant/thermophysicalTransport');
changed['constant/thermophysicalTransport']=once(transport,/laminar\s*\{\s*model\s+Fourier\s*;\s*\}/,
  'RAS { model eddyDiffusivity; Prt 0.7; }','thermal transport selection');
let control=await read('system/controlDict');
if(/fgmRansUnityLeDiagnostic/.test(control))throw Error('RAS diagnostic already selected');
control+='\nfgmRansUnityLeDiagnostic yes;\n';
const densityFlags=[...control.matchAll(/\bconserveTabulatedDensity\s+(yes|no)\s*;/g)];
if(!densityFlags.length)control+='conserveTabulatedDensity yes;\n';
else if(densityFlags.length!==1||densityFlags[0][1]!=='yes')throw Error('Conservative tabulated density required');
control=once(control,/functions\s*\{/,
  'functions {\n ransWallYPlus { type yPlus; libs ("libfieldFunctionObjects.so"); writeControl writeTime; }\n ransTurbulenceRange { type fieldMinMax; libs ("libfieldFunctionObjects.so"); fields (k epsilon nut alphat); location true; writeControl writeTime; }','functions dictionary');
changed['system/controlDict']=control;
let solution=await read('system/fvSolution');
if(/\b(?:k|epsilon)\b/.test(solution))throw Error('Unexpected pre-existing turbulence solver');
changed['system/fvSolution']=once(solution,/solvers\s*\{/,
  'solvers {\n "(k|epsilon).*" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0; }','solver dictionary');
let schemes=await read('system/fvSchemes');
if(/div\(phi,(?:k|epsilon)\)/.test(schemes))throw Error('Unexpected turbulence convection scheme');
changed['system/fvSchemes']=once(schemes,/divSchemes\s*\{/,
  'divSchemes {\n div(phi,k) Gauss upwind; div(phi,epsilon) Gauss upwind;','divergence dictionary');
const z=await readFile(`${root}/0/Z`,'utf8');
const axis=/axisymmetric\s*\{\s*type\s+(\w+)\s*;\s*\}/.exec(z)?.[1];
if(!['empty','symmetry','symmetryPlane'].includes(axis))throw Error('Unsupported axis boundary');
const k=config.initial.k_m2_s2;
const epsilon=Math.pow(0.09,0.75)*Math.pow(k,1.5)/config.initial.length_m;
const nut=0.09*k*k/epsilon;
const header=(name,dim,value,patches)=>`FoamFile { version 2.0; format ascii; class volScalarField; object ${name}; }
dimensions [${dim}]; internalField uniform ${value};
boundaryField {
 ${patches}
 axisymmetric { type ${axis}; }
 planeMinus { type wedge; } planePlus { type wedge; }
}\n`;
const inlets=(kind,value)=>Object.entries(config.inlets).map(([name,v])=>
  `${name} { type ${kind==='k'?'turbulentIntensityKineticEnergyInlet':'turbulentMixingLengthDissipationRateInlet'};
 ${kind==='k'?`intensity ${v.intensity};`:`mixingLength ${v.length_m};`} value uniform ${value}; }`).join('\n');
const transportedWalls=(kind,value)=>`geom { type ${kind==='k'?'kqRWallFunction':'epsilonWallFunction'}; value uniform ${value}; }
 noslipwalls { type ${kind==='k'?'kqRWallFunction':'epsilonWallFunction'}; value uniform ${value}; }
 slipwalls { type zeroGradient; }
 outlet { type inletOutlet; inletValue uniform ${value}; value uniform ${value}; }`;
changed['0/k']=header('k','0 2 -2 0 0 0 0',k,transportedWalls('k',k)+'\n'+inlets('k',k));
changed['0/epsilon']=header('epsilon','0 2 -3 0 0 0 0',epsilon,transportedWalls('epsilon',epsilon)+'\n'+inlets('epsilon',epsilon));
const calculated=value=>['loxinlet','ch4inlet','outlet','slipwalls'].map(name=>`${name} { type calculated; value uniform ${value}; }`).join('\n');
changed['0/nut']=header('nut','0 2 -1 0 0 0 0',nut,
  `geom { type nutkWallFunction; value uniform 0; } noslipwalls { type nutkWallFunction; value uniform 0; }\n`+calculated(nut));
changed['0/alphat']=header('alphat','1 -1 -1 0 0 0 0',0,
  'geom { type fixedValue; value uniform 0; } noslipwalls { type fixedValue; value uniform 0; }\n'+calculated(0));
const zeroNames=await readdir(`${root}/0`);
if(['k','epsilon','nut','alphat'].some(n=>zeroNames.includes(n)))throw Error('Turbulence fields already exist');
const report={schema:'g2-rans-diagnostic-preparation/v1',case:root,config,configSha256:hash(configRaw),
  originalManifestSha256:hash(manifestRaw),initialSeed:{k,epsilon,nut},
  inletFormula:'k=1.5*(I*|actual U|)^2; epsilon=Cmu^0.75*k^1.5/L; Cmu=0.09',
  policy:'RAS kEpsilon; eddyDiffusivity; fixed-chi delta-PDF; Prt=Sct=0.7',
  files:Object.fromEntries(Object.entries(changed).map(([name,value])=>[name,{beforeSha256:original[name]?hash(original[name]):null,afterSha256:hash(value)}])),
  scientificAcceptance:false,thermoOrMeanFlowInputsChanged:false};
m.ransDiagnostic=report;
m.steadyFlamelet.pdf='delta at mean Z; no scalar-variance closure';
m.approximations=m.approximations.filter(s=>s!=='laminar resolved diagnostic').concat([
  'RANS kEpsilon mean-mixing diagnostic with fixed-chi delta-PDF composition',
  'Prt=Sct=0.7 unity turbulent Lewis approximation; not Sharma LES Prt0.85',config.provenance]);
if(action!=='--apply'){console.log(JSON.stringify({dryRun:true,...report},null,2));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Mutation requires the admitted Slurm allocation');
for(const [name,value] of Object.entries(original)){
  const backup=`${root}/rans-original/${name}`;await mkdir(dirname(backup),{recursive:true});await writeFile(backup,value,{flag:'wx'});
}
await writeFile(`${root}/rans-original/direct-g2-input.json`,manifestRaw,{flag:'wx'});
for(const [name,value] of Object.entries(changed))await writeFile(`${root}/${name}`,value);
await writeFile(`${root}/direct-g2-input.json`,JSON.stringify(m,null,2)+'\n');
await writeFile(`${root}/rans-diagnostic.json`,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({prepared:true,...report},null,2));
