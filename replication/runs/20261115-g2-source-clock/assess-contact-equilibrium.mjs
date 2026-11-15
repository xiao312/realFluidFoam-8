import fs from 'node:fs';import crypto from 'node:crypto';
const[profiles,out,action]=process.argv.slice(2);
if(!profiles||!out||![undefined,'--apply'].includes(action))throw Error('Use PROFILES_JSON OUTPUT_JSON [--apply]');
const raw=fs.readFileSync(profiles),data=JSON.parse(raw),limits={pressureRelative:1e-6,velocityRelative:1e-6};
const cases=Object.entries(data).map(([nx,row])=>{
 const p=Math.max(...row.p_MPa.map(v=>Math.abs(v/6-1))),u=Math.max(...row.U_m_s.map(v=>Math.abs(v/10-1)));
 return{label:nx,nx:Number(row.entry.nx),cells:row.x_m.length,sampleTime_s:row.entry.time_s,solverExit:row.entry.result.solverExit,pressureRelativeDeparture:p,velocityRelativeDeparture:u,pressureEquilibriumPassed:p<=limits.pressureRelative,velocityEquilibriumPassed:u<=limits.velocityRelative,completedRequestedTime:row.entry.time_s===.02&&row.entry.result.solverExit===0};
});
const receipt={readOnly:action!=='--apply',sourceProfilesSha256:crypto.createHash('sha256').update(raw).digest('hex'),limits,cases,numericalEquilibriumQualified:cases.every(c=>c.completedRequestedTime&&c.pressureEquilibriumPassed&&c.velocityEquilibriumPassed),scientificAcceptance:false,humanAcceptance:'not_assessed',note:'Original contact equilibrium limits retained. Conservation/source checks are separate; their pass cannot approve pressure equilibrium.'};
if(action==='--apply')fs.writeFileSync(out,JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt,null,2));
