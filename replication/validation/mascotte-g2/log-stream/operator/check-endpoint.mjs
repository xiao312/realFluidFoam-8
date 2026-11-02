import{scanSolverLog}from'../reader.mjs';
import{writeJson}from'../json.mjs';
const maximum=(values,seed=-Infinity)=>values.reduce((m,v)=>Math.max(m,v),seed);
import{readFile,writeFile}from'node:fs/promises';import{createHash}from'node:crypto';
const[root,mode,code]=process.argv.slice(2);if(!root||!['strict','enabled'].includes(mode))throw Error('Use CASE strict|enabled EXIT');
const target=JSON.parse(await readFile(`${root}/direct-g2-input.json`)).endTime;
const scanned=await scanSolverLog(`${root}/log.solver`),log=scanned.markerText,limit=64*Number.EPSILON;
const records=prefix=>scanned.lines(prefix).map(line=>Object.fromEntries([...line.matchAll(/(\w+)=([^\s]+)/g)].map(([,k,v])=>[k,Number.isFinite(Number(v))?Number(v):v])));
const inputs=records('steadyEndpointInput'),representations=records('steadyEndpointRepresentation');
const dynamic=inputs.filter(r=>r.t>0),attempts=[...log.matchAll(/^Time =\s+(\S+)/gm)].map(m=>Number(m[1]));
const failures=[];const check=(pass,name)=>{if(!pass)failures.push(name);};
check(inputs.length>0&&dynamic.length>0,'Actual global initial/dynamic witnesses missing');
check(inputs.every(r=>r.nonfiniteCount===0&&Number.isFinite(r.maxOutsideDelta)&&r.maxOutsideDelta<=limit&&r.limit===limit),'Nonfinite/material global coordinate excursion');
if(mode==='strict'){
 check(Number(code)===1,'Strict control did not produce the expected solver exit1');
 check(attempts.length===1&&!/^ExecutionTime =/m.test(log),'Strict control must stop on its first attempted update');
 check(inputs.every(r=>r.policy==='strict'),'Strict default was not executed');
 check(dynamic.some(r=>r.maxOutsideDelta>0),'No actual endpoint excursion measured');
 check(/FOAM FATAL ERROR/.test(log)&&/endpoint-coordinate rawZ=/.test(log)&&/policy=strict/.test(log),'Expected precise strict endpoint failure missing');
 check(!/out of temperature range|Floating point exception/.test(log),'Unexpected physical failure');
}else{
 const verdict=JSON.parse(await readFile(`${root}/direct-g2-result.json`));
 check(Number(code)===0&&Object.values(verdict.mechanicalChecks).every(Boolean)&&verdict.time===target,'Actual cold requested-duration mechanical completion missing');
 check(inputs.every(r=>r.policy==='endpoint64epsilon'),'Optional policy not explicitly executed');
 check(representations.length===inputs.length&&representations.every(r=>r.transportedZModified===0&&r.maxCoordinateDelta<=limit&&r.maxElementCoordinateDelta<=limit),'Lookup representation accounting missing/outside bound');
 // Field projection is checked independently; lookup mapping may now be unused.
}
const report={mode,passed:failures.length===0,failures,solverExit:Number(code),logSha256:scanned.identity.sha256,logInputIdentity:scanned.identity,
 fixedLimit:limit,attemptedTimes_s:attempts,globalInputWitnesses:inputs,representations,
 maximumObservedExcursion:maximum(inputs.map(r=>r.maxOutsideDelta)),transportedFieldModifiedByPolicy:false,
 mappedQueryCount:representations.reduce((n,r)=>n+r.mappedCells+r.mappedPatchCalls,0),
 countInterpretation:'Queries across corrections, not unique cells; element delta is implied by changing only the lookup coordinate.',scientificAcceptance:false};
await writeJson(`${root}/endpoint-qualification.json`,report);
console.log(JSON.stringify({mode,passed:report.passed,failures,maximumObservedExcursion:report.maximumObservedExcursion,mappedQueryCount:report.mappedQueryCount}));
if(!report.passed)process.exitCode=1;
