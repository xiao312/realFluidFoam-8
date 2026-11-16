import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';

const options={};
for(let i=2;i<process.argv.length;i+=2){
  const key=process.argv[i];
  if(!['--case','--log','--out'].includes(key)||!process.argv[i+1]||options[key])
    throw Error('Use --case COLLECTED_CASE --log RETAINED_LOG [--out NEW_JSON]');
  options[key]=resolve(process.argv[i+1]);
}
if(!options['--case']||!options['--log'])throw Error('Explicit case and retained log required');
const root=options['--case'],sha=b=>createHash('sha256').update(b).digest('hex');
const manifestRaw=await readFile(root+'/direct-g2-input.json'),manifest=JSON.parse(manifestRaw);
if(manifest.startTime!==0||manifest.energyForm!=='absoluteEnthalpy')throw Error('Original-zero absolute-Ha case required');
const raw=await readFile(options['--log']),text=raw.toString();
function records(prefix,keys){
  const last=new Map();
  for(const line of text.split(/\r?\n/))if(line.startsWith(prefix+' ')){
    const row=Object.fromEntries([...line.matchAll(/(\w+)=([^\s]+)/g)].map(m=>[m[1],Number(m[2])]));
    if(keys.some(k=>!Number.isFinite(row[k])))throw Error(`Missing/nonfinite ${prefix} record`);
    last.set(row.t,row);
  }
  return [...last.values()].sort((a,b)=>a.t-b.t);
}
const states=records('energyState',['t','H','mass']),equations=records('energyEquation',
  ['t','ddtW','convectionW','diffusionW','kineticW','pressureW','sourceW','residualL1W']);
if(states.length<2||states[0].t!==0)throw Error('At least two actual states including original zero required');
const tolerance=t=>Math.max(1e-14,Math.abs(t)*1e-8);
function matched(rows,time){
  const found=rows.filter(r=>Math.abs(r.t-time)<=tolerance(time));
  if(found.length>1)throw Error('Ambiguous recorded time');
  return found[0];
}
const first=states[0],last=states.at(-1),missingEquations=[];
let integratedDdt=0,integratedOther=0,integratedAbsoluteTerms=0,integratedResidualL1=0;
for(let i=1;i<states.length;i++){
  const state=states[i],dt=state.t-states[i-1].t,equation=matched(equations,state.t);
  if(!(dt>0))throw Error('Nonpositive physical timestep');
  if(!equation){missingEquations.push(state.t);continue;}
  const terms=['convectionW','diffusionW','kineticW','pressureW'].map(k=>equation[k]);
  integratedDdt+=dt*equation.ddtW;
  integratedOther+=dt*(terms.reduce((a,b)=>a+b,0)-equation.sourceW);
  integratedAbsoluteTerms+=dt*(Math.abs(equation.ddtW)+Math.abs(equation.sourceW)+terms.reduce((a,b)=>a+Math.abs(b),0));
  integratedResidualL1+=dt*equation.residualL1W;
}
const fluxInputs={},fluxes={},patches=['loxinlet','ch4inlet','outlet'];
let boundaryUnavailable=null;
try{
  for(const patch of patches){
    const rows=new Map(),folder=root+'/postProcessing/massFlux_'+patch;
    for(const stamp of await readdir(folder)){
      if(!Number.isFinite(Number(stamp)))continue;
      for(const name of await readdir(folder+'/'+stamp)){
        if(!name.endsWith('.dat'))continue;
        const path=folder+'/'+stamp+'/'+name,bytes=await readFile(path);fluxInputs[path]=sha(bytes);
        for(const line of bytes.toString().split(/\r?\n/)){
          if(!line.trim()||line.trim().startsWith('#'))continue;
          const values=line.trim().split(/\s+/).map(Number);
          if(values.length!==2||values.some(v=>!Number.isFinite(v)))throw Error('Expected scalar boundary mass-flux records');
          rows.set(values[0],{t:values[0],flux:values[1]});
        }
      }
    }
    fluxes[patch]=[...rows.values()];
  }
}catch(error){boundaryUnavailable=error.message;}
const missingBoundary=[],inletErrors={loxinlet:0,ch4inlet:0};let boundaryIntegral=0;
if(!boundaryUnavailable)for(let i=1;i<states.length;i++){
  const state=states[i],dt=state.t-states[i-1].t,rows=patches.map(p=>matched(fluxes[p],state.t));
  if(rows.some(r=>!r)){missingBoundary.push(state.t);continue;}
  boundaryIntegral+=dt*rows.reduce((s,r)=>s+r.flux,0);
  for(let j=0;j<2;j++){
    const patch=patches[j],expected=-manifest.streams[patch].massFlow_kg_s;
    inletErrors[patch]=Math.max(inletErrors[patch],Math.abs(rows[j].flux/expected-1));
  }
}
const equationComplete=missingEquations.length===0,boundaryComplete=!boundaryUnavailable&&!missingBoundary.length;
const enthalpyChange=last.H-first.H,massChange=last.mass-first.mass;
const report={schema:'g2-accepted-state-equation-budget/v1',startTime_s:first.t,endTime_s:last.t,
  physicalSteps:states.length-1,declaredEndTime_s:manifest.endTime,
  reachedDeclaredEnd:Math.abs(last.t-manifest.endTime)<=tolerance(manifest.endTime),
  equation:equationComplete?{
    stateHaChange_J:enthalpyChange,assembledDdtIntegral_J:integratedDdt,
    stateMinusAssembledDdt_J:enthalpyChange-integratedDdt,
    assembledOtherTermsIntegral_J:integratedOther,
    stateEquationBalanceResidual_J:enthalpyChange+integratedOther,
    assembledSignedBalanceResidual_J:integratedDdt+integratedOther,
    recordedResidualL1Integral_J:integratedResidualL1,
    absoluteTermIntegral_J:integratedAbsoluteTerms,
    stateEquationResidualOverAbsoluteTerms:(enthalpyChange+integratedOther)/Math.max(1e-300,integratedAbsoluteTerms),
    interpretation:'Last physical-time Euler Ha equation only; includes assembled kinetic/pressure terms. Not an independent total-energy proof.'
  }:{status:'unavailable',missingTimes_s:missingEquations},
  boundaryMass:boundaryComplete?{
    quadrature:'Euler right endpoint at every recorded physical timestep',massChange_kg:massChange,
    outwardFluxIntegral_kg:boundaryIntegral,residual_kg:massChange+boundaryIntegral,
    residualOverInitialMass:(massChange+boundaryIntegral)/first.mass,
    inletMaximumRelativeFluxError:inletErrors
  }:{status:'unavailable',reason:boundaryUnavailable,missingTimes_s:missingBoundary},
  inputHashes:{log:sha(raw),manifest:sha(manifestRaw),fluxes:fluxInputs},
  codeSha256:sha(await readFile(new URL(import.meta.url))),scientificAcceptance:false,
  acceptanceThresholdIntroduced:false,readOnly:!options['--out']};
if(options['--out'])await writeFile(options['--out'],JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(report,null,2));
