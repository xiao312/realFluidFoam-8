import{scanSolverLog}from'../reader.mjs';
import{writeJson}from'../json.mjs';
const maximum=(values,seed=-Infinity)=>values.reduce((m,v)=>Math.max(m,v),seed);
import{readFile,writeFile}from'node:fs/promises';import{createHash}from'node:crypto';
const[root,mode,code]=process.argv.slice(2);if(!root||!['baseline','candidate'].includes(mode)||!/^\d+$/.test(code))throw Error('Use CASE MODE SOLVER_EXIT');
const target=JSON.parse(await readFile(`${root}/direct-g2-input.json`)).endTime;
const scanned=await scanSolverLog(`${root}/log.solver`),log=scanned.markerText;
const records=prefix=>scanned.lines(prefix).map(line=>Object.fromEntries([...line.matchAll(/(\w+)=([^\s]+)/g)].map(([,k,v])=>[k,Number.isFinite(Number(v))?Number(v):v])));
const stages=records('fgmContinuityStage'),endpoint=records('steadyEndpointInput'),failures=[];
const check=(v,message)=>{if(!v)failures.push(message);},by=name=>stages.filter(r=>r.stage===name),peak=name=>maximum(by(name).map(r=>r.maxContinuityKg_s),0);
check(stages.length>0&&stages.every(r=>['t','maxContinuityKg_s','sumContinuityKg_s','massKg'].every(k=>Number.isFinite(r[k]))&&r.fieldsModified===0),'Missing or invalid stage witnesses');
check(by('beforePressureLimit').length>0&&by('afterPressureEOSDensity').length===by('beforePressureLimit').length,'Pressure reset stage pairs missing');
let finalReset=[];
if(mode==='baseline'){
 check(Number(code)===1&&/endpoint-coordinate rawZ=/.test(log)&&/FOAM FATAL ERROR/.test(log)&&!/^ExecutionTime =/m.test(log),'Retained first-step endpoint failure not reproduced');
 check(by('afterPressureDensitySolve').length===0,'Default-off baseline performed the candidate solve');
 check(peak('afterPressureEOSDensity')>1000*peak('beforePressureLimit'),'Staged density-reset continuity growth not demonstrated');
 const observed=maximum(endpoint.map(r=>r.maxOutsideDelta));
 check(Math.abs(observed-4.6458263902593444e-9)<=1e-12,'Baseline endpoint witness differs materially from retained126434026');
}else{
 const verdict=JSON.parse(await readFile(`${root}/direct-g2-result.json`));
 const bound=JSON.parse(await readFile(`${root}/endpoint-qualification.json`));
 check(Number(code)===0&&verdict.time===target&&Object.values(verdict.mechanicalChecks).every(Boolean)&&bound.passed,'Actual requested-duration mechanical/endpoint qualification missing');
 check(by('afterPressureDensitySolve').length===by('afterPressureEOSDensity').length,'Candidate continuity solve stage missing');
 const before=by('beforeFinalEOSDensity'),after=by('afterFinalEOSDensity');
 check(before.length>0&&before.length===after.length,'Final EOS reset witnesses missing');
 finalReset=before.map((r,i)=>({t:r.t,beforeMassKg:r.massKg,afterMassKg:after[i].massKg,massChangeKg:after[i].massKg-r.massKg,
  beforeMaxContinuityKg_s:r.maxContinuityKg_s,afterMaxContinuityKg_s:after[i].maxContinuityKg_s}));
 check(finalReset.every((r,i)=>r.t===after[i].t),'Final EOS reset stage times differ');
}
const report={mode,passed:failures.length===0,failures,solverExit:Number(code),logSha256:scanned.identity.sha256,logInputIdentity:scanned.identity,stages,
 maxima:Object.fromEntries(['beforePressureLimit','afterPressureEOSDensity','afterPressureDensitySolve','beforeFinalEOSDensity','afterFinalEOSDensity'].map(k=>[k,peak(k)])),
 finalEOSReset:finalReset,wholeStepConservationEstablished:false,scientificAcceptance:false};
await writeJson(`${root}/density-consistency-result.json`,report);
console.log(JSON.stringify({mode,passed:report.passed,failures,maxima:report.maxima,finalEOSResetSteps:finalReset.length}));
if(!report.passed)process.exitCode=1;
