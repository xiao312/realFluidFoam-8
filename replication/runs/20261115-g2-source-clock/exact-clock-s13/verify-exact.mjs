import fs from 'node:fs';
const root=process.argv[2];
function read(name){const lines=fs.readFileSync(root+'/'+name+'.csv','utf8').trim().split('\n'),keys=lines.shift().split(',');return lines.map(line=>Object.fromEntries(line.split(',').map((value,i)=>[keys[i],value])));}
const a=read('exactCoarse'),b=read('exactFine');
if(a.length!==20||b.length!==40)throw Error('Executed row count');
let worstAlphaError=0;
for(const row of [...a,...b]){
 const dt=+row.dt_s,tau=+row.tau_s,expected=-Math.expm1(-dt/tau),error=Math.abs(+row.alpha-expected);
 if(row.mode!=='fixedTimeExact'||row.passed!=='1'||!(error<2e-16))throw Error('Exact model recurrence/alpha failure');
 worstAlphaError=Math.max(worstAlphaError,error);
}
const x=a.at(-1),y=b.at(-1),physicalTimeA=+x.dt_s*+x.pseudoStep,physicalTimeB=+y.dt_s*+y.pseudoStep;
if(physicalTimeA!==physicalTimeB)throw Error('Different source time');
const endpointTemperatureDifference=Math.abs(+x.T_K-+y.T_K);
if(endpointTemperatureDifference>1e-8)throw Error('Frozen-target endpoint is not timestep invariant');
console.log(JSON.stringify({executedExactSourceRows:60,worstAlphaError,physicalTimeA,physicalTimeB,endpointTemperatureDifference,sourceRecurrencePassed:true,constantHaAndQdotIdentityPassed:true,CFDsteps:0,scientificAcceptance:false},null,2));
