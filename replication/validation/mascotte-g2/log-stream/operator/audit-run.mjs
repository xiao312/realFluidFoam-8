import {createReadStream}from'node:fs';
// Run only after the case process has returned, inside its admitted allocation.
import {readFile,writeFile,readdir,stat} from 'node:fs/promises';
import {openSync,closeSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const [root,build,out,auditor]=process.argv.slice(2),hash=b=>createHash('sha256').update(b).digest('hex');
if(!root||!build||!out||!auditor||!process.env.SLURM_JOB_ID)throw Error('Allocated CASE BUILD OUT AUDITOR required');
async function bound(path){const digest=createHash('sha256');for await(const chunk of createReadStream(path))digest.update(chunk);return{path,sha256:digest.digest('hex')};}
async function findFlux(path){
 let entries;try{entries=await readdir(path,{withFileTypes:true});}catch(e){if(e.code==='ENOENT')return[];throw e;}
 const files=[];for(const entry of entries){const child=`${path}/${entry.name}`;if(entry.isDirectory())files.push(...await findFlux(child));else if(entry.name==='surfaceFieldValue.dat')files.push(await bound(child));}
 return files.sort((a,b)=>a.path.localeCompare(b.path));
}
const receiptRaw=await readFile(`${build}/build-qualification.json`),receipt=JSON.parse(receiptRaw);
const binary=receipt.products.find(p=>p.file==='bin/reactingFoamSolveZ');
if(!receipt.compile_link_help_passed||receipt.custom_library_count!==15||!binary)throw Error('Missing qualified runtime receipt');
const sourceFiles={};for(const name of ['EEqn.H','energyState.H','pEqn.H','reactingFoamSolveZ.C'])sourceFiles[name]=await bound(`${build}/source/applications/solvers/reactingFoamSolveZ/${name}`);
const massFluxFiles={};for(const patch of ['ch4inlet','loxinlet','outlet'])massFluxFiles[patch]=await findFlux(`${root}/postProcessing/massFlux_${patch}`);
const m={schema:'g2-discrete-conservation-input-v1',jobId:process.env.SLURM_JOB_ID,
 solverSourceCommit:receipt.source,solverExecutableSha256:binary.sha256,staticMesh:true,energyForm:'absoluteEnthalpy',
 log:await bound(`${root}/log.solver`),sourceFiles,
 caseFiles:{controlDict:await bound(`${root}/system/controlDict`),fvSchemes:await bound(`${root}/system/fvSchemes`)},
 executionReceipt:{path:`${build}/build-qualification.json`,sha256:hash(receiptRaw)},massFluxFiles,
 boundaryCoverage:{zeroFluxPatches:['geom','slipwalls','noslipwalls','axisymmetric','planeMinus','planePlus'],unverifiedPatches:Object.keys(massFluxFiles).filter(p=>!massFluxFiles[p].length),justification:'Declared impermeable/wedge/symmetry boundaries; omitted patch flux not independently sampled'},
 unloggedMassSources:'No independent fvOptions source sample; preserve interpretation limit',
 unloggedEnergySources:'Compare assembled term sum with residual; no independent fvOptions power sample'};
const manifest=`${out}/conservation-input.json`;await writeFile(manifest,JSON.stringify(m,null,2)+'\n',{flag:'wx'});
const fd=openSync(`${out}/conservation-audit.log`,'wx');let result;
try{result=spawnSync(process.execPath,['--max-old-space-size=8192',`${auditor}/audit.mjs`,manifest,'--out',`${out}/conservation-full`],{stdio:['ignore',fd,fd],timeout:240000});}finally{closeSync(fd);}
if(result.status!==0)throw Error(`Allocated conservation audit failed status=${result.status} signal=${result.signal}; retained log/manifest remain`);
const reportPath=`${out}/conservation-full/report.json`,summary=JSON.parse(await readFile(`${out}/conservation-full/summary.json`));
await writeFile(`${out}/conservation-summary.json`,JSON.stringify({...summary,fullReportPath:reportPath,stepsCsvPath:`${out}/conservation-full/steps.csv`,completeRetainedLogRead:true,logBytes:(await stat(`${root}/log.solver`)).size,scientificAcceptance:false},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:summary.status,completedThroughTime_s:summary.completedThroughTime_s,steps:summary.perStepRecordsRetained,smallExport:`${out}/conservation-summary.json`,scientificAcceptance:false}));
