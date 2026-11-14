import {readFile,writeFile,readdir} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const options={},args=process.argv.slice(2);let apply=false;
for(let i=0;i<args.length;i++){
  if(args[i]==='--apply'){apply=true;continue;}
  if(!['--case','--point','--pressure'].includes(args[i])||!args[i+1]||options[args[i]])throw Error('Use --case NEW_POINT_CASE --point POINT_JSON [--pressure PA] [--apply]');
  options[args[i]]=args[++i];
}
if(!options['--case']||!options['--point'])throw Error('Explicit case and point required');
const root=path.resolve(options['--case']),pointRaw=await readFile(options['--point']),point=JSON.parse(pointRaw);
if(point.schema!=='captured-failed-thermo-point/v1'||point.authorizedForCFDRestart!==false)throw Error('Captured query point required');
if((await readdir(root)).some(n=>/^processor/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0)))throw Error('Fresh undecomposed point case required');
const hash=raw=>createHash('sha256').update(raw).digest('hex');
if(hash(await readFile(`${root}/constant/thermophysicalProperties`))!==point.thermoDictionarySha256)throw Error('Exact thermo dictionary differs from captured point');
const zeroNames=(await readdir(`${root}/0`)).filter(n=>!['p','T','Ha'].includes(n));
if(zeroNames.slice().sort().join()!==point.species.slice().sort().join())throw Error('Exact species inventory differs');
const pressure=Number(options['--pressure']??point.pressure_Pa),temperature=point.temperature_K;
if(!Number.isFinite(pressure)||pressure<=0||!Number.isFinite(temperature)||temperature<60||temperature>6000)throw Error('Invalid query pressure/temperature');
const changes=[];
function uniform(before,value){if(!/internalField uniform [^;]+;/.test(before))throw Error('Expected fresh uniform point field');return before.replace(/internalField uniform [^;]+;/,`internalField uniform ${value};`);}
for(const name of point.species){const file=`${root}/0/${name}`,before=await readFile(file,'utf8');changes.push({file,before,after:uniform(before,point.massFractions[name])});}
for(const [name,value] of [['p',pressure],['T',temperature]]){const file=`${root}/0/${name}`,before=await readFile(file,'utf8');changes.push({file,before,after:uniform(before,value)});}
const temperatures=[...new Set([...Array.from({length:41},(_,i)=>temperature-10+i*.5),...[-.1,-.01,-.001,-.0001,-.00001,0,.00001,.0001,.001,.01,.1].map(d=>temperature+d)].filter(t=>t>=60&&t<=6000))].sort((a,b)=>a-b);
const guesses=[temperature-5,temperature-.5,temperature,temperature+.5,temperature+5,300].filter(t=>t>=60&&t<=6000);
const file=`${root}/constant/probeProperties`,before=await readFile(file,'utf8');
const after=before.replace(/pressure [^;]+;/,`pressure ${pressure};`).replace(/temperatures \([^)]*\);/,`temperatures (${temperatures.join(' ')});`).replace(/increments \([^)]*\);/,'increments (0.001);')+`\nenthalpyTargets (${point.storedHs_J_kg});\ntargetGuesses (${guesses.join(' ')});\ntargetCorrectionPasses 12;\ntargetRelativeLimit 1e-8;\nwriteSrkCoefficients yes;\n`;
changes.push({file,before,after});
const sha=s=>createHash('sha256').update(s).digest('hex');
const receipt={schema:'captured-enthalpy-point-queries/v1',pointSha256:sha(pointRaw),sourceCase:point.sourceCase,snapshotTime:point.snapshotTime,cell:point.cell,rank:point.rank,CFD_steps:0,pressure_Pa:pressure,capturedPressure_Pa:point.pressure_Pa,temperature_K:temperature,targetHs_J_kg:point.storedHs_J_kg,compositionNormalized:false,acceptanceChanged:false,changes:changes.map(c=>({file:c.file,beforeSha256:sha(c.before),afterSha256:sha(c.after)}))};
if(!apply){console.log(JSON.stringify({readOnly:true,...receipt},null,2));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Allocated point configuration required');
for(const c of changes)await writeFile(c.file,c.after);
await writeFile(`${root}/point-input.json`,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(receipt));
