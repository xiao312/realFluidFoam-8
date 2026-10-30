import{readFile,readdir,writeFile}from'node:fs/promises';
import{resolve}from'node:path';
import{scalarValues}from'../direct-fgm/diagnostics.mjs';
const[casePath]=process.argv.slice(2);if(!casePath)throw Error('Use check-periodic.mjs CASE');
const root=resolve(casePath),m=JSON.parse(await readFile(`${root}/verification-input.json`)),log=await readFile(`${root}/log.solver`,'utf8');
if(m.schema!=='steady-flamelet-periodic-v1')throw Error('Wrong case kind');
const lines=log.split(/\r?\n/),record=prefix=>lines.filter(l=>l.startsWith(prefix)).map(l=>Object.fromEntries(l.trim().split(/\s+/).slice(1).filter(x=>x.includes('=')).map(x=>{const[k,v]=x.split('=');return[k,Number(v)];})));
const states=record('energyState '),equations=record('energyEquation '),refreshes=record('steadyFlamelet t='),caloric=record('thermoClosure ');
const positive=(await readdir(root)).filter(n=>Number.isFinite(Number(n))&&Number(n)>0).sort((a,b)=>Number(a)-Number(b));
const last=positive.at(-1),fields={};
if(last)for(const name of ['Z','c','CO','CO2','T','Ha','rho','p'])fields[name]=scalarValues(await readFile(`${root}/${last}/${name}`,'utf8'),name);
const at=(name,i)=>fields[name]?.[fields[name]?.length===1?0:i];
let order=true,lastEnergy=-1;
for(let i=0;i<lines.length;i++)if(lines[i].startsWith('energyEquation ')){
 const segment=lines.slice(lastEnergy+1,i),z=segment.map(l=>l.startsWith('fgmZ:')).lastIndexOf(true),y=segment.map(l=>l.startsWith('steadyFlamelet t=')).lastIndexOf(true);
 if(z<0||y<=z)order=false;lastEnergy=i;
}
const checks={
 freshStart:m.startTime===0&&states[0]?.t===0,
 normalEnd:/\nEnd\s*(?:\n|$)/.test(log)&&!/FOAM FATAL|Floating point exception|out of temperature range/.test(log),
 reachedEndpoint:Math.abs((states.at(-1)?.t??-1)-m.endTime)<1e-14&&Math.abs(Number(last)-m.endTime)<1e-14,
 noProgressTransportOrSource:!/Solving for c,|fgmSourceStage |fgmAppliedSource /.test(log),
 noAddedChemicalHeat:equations.length>0&&equations.every(r=>r.sourceW===0),
 compositionAfterTransportBeforeEnergy:order&&refreshes.length>=equations.length+1,
 compositionIntegrity:refreshes.length>0&&refreshes.every(r=>r.maxSumError<=1e-8&&r.maxBoundaryLookupError<=1e-8&&r.transportedProgress===0),
 caloricInversion:caloric.length>0&&caloric.every(r=>r.invalid===0&&r.maxRelative<=r.limit&&r.boundaryMaxRelative<=r.limit),
 finiteFields:Object.keys(fields).length===8&&Object.values(fields).every(a=>a.every(Number.isFinite)),
 derivedProgress:last&&Array.from({length:m.cells},(_,i)=>Math.abs(at('c',i)-at('CO',i)-at('CO2',i))<1e-12).every(Boolean),
};
const first=states[0],final=states.at(-1),energy=s=>s?s.H+s.K-s.PV:null;
const report={schema:'steady-flamelet-periodic-result/v1',checks,mechanicalCompletion:Object.values(checks).every(Boolean),
 inputHashes:m.inputHashes,initialEnergy:first??null,finalEnergy:final??null,
 totalEnergyChange_J:first&&final?energy(final)-energy(first):null,massChange_kg:first&&final?final.mass-first.mass:null,
 equations:equations.length,refreshes:refreshes.length,fields:Object.fromEntries(Object.entries(fields).map(([k,v])=>[k,{min:Math.min(...v),max:Math.max(...v)}])),
 sourceProfileSteady:m.sourceTableOriginalSteadyConverged,physicalValidation:false,scientificAcceptance:false,
 interpretation:'Actual fixed-chi composition/Ha transport lifecycle diagnostic. Changes in final-state energy require pressure-stage/conservation analysis, not a synthetic flame-source expectation.'};
await writeFile(`${root}/steady-periodic-result.json`,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
if(!report.mechanicalCompletion)process.exitCode=2;
