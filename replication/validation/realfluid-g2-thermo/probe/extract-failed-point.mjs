import {readFile, writeFile, realpath} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';

const options={}, args=process.argv.slice(2);
for(let i=0;i<args.length;i+=2){
  if(!['--case','--time','--rank','--cell','--out'].includes(args[i])||!args[i+1]||options[args[i]])throw Error('Use --case CASE --time EXACT_TIME --cell N [--rank N] [--out NEW_JSON]');
  options[args[i]]=args[i+1];
}
const root=await realpath(options['--case']??''), time=options['--time'];
const cell=Number(options['--cell']),rank=options['--rank']===undefined?null:Number(options['--rank']);
if(!time||!/^(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/.test(time)||!Number.isFinite(Number(time))||Number(time)<=0||!Number.isInteger(cell)||cell<0||rank!==null&&(!Number.isInteger(rank)||rank<0))throw Error('Explicit positive snapshot time and nonnegative integer cell/rank required');
const directory=await realpath(path.join(root,rank===null?'':`processor${rank}`,time));
if(!directory.startsWith(root+path.sep))throw Error('Snapshot escapes source case');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const clean=text=>text.replace(/\/\*[\s\S]*?\*\//g,'').replace(/\/\/[^\n]*/g,'');
const dictionary=await readFile(path.join(root,'constant/thermophysicalProperties'));
const inventory=clean(dictionary.toString()).match(/\bspecies\s*\(([\s\S]*?)\)\s*;/)?.[1];
const species=inventory?.match(/"(?:\\.|[^"\\])*"|[^\s"]+/g)?.map(n=>n.startsWith('"')?JSON.parse(n):n);
if(!species?.length||new Set(species).size!==species.length||species.some(n=>!/^[A-Za-z0-9_()]+$/.test(n)))throw Error('Invalid exact species inventory');
const fields={};
async function scalar(name){
  const file=await realpath(path.join(directory,name));
  if(!file.startsWith(directory+path.sep))throw Error('Field escapes snapshot');
  const raw=await readFile(file),text=clean(raw.toString());
  if(!/\bclass\s+volScalarField\s*;/.test(text))throw Error(`Expected scalar field ${name}`);
  const object=text.match(/\bobject\s+("[^"]+"|[^\s;]+)\s*;/)?.[1];
  const objectName=object?.startsWith('"')?JSON.parse(object):object;
  if(objectName!==name)throw Error(`Field object identity mismatch ${name}/${objectName}; possible case-insensitive filesystem collision`);
  const uniform=text.match(/\binternalField\s+uniform\s+([^;]+);/);
  const nonuniform=text.match(/\binternalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(([\s\S]*?)\)\s*;/);
  let value;
  if(uniform)value=Number(uniform[1]);
  else if(nonuniform){
    const values=nonuniform[2].trim().split(/\s+/).map(Number);
    if(values.length!==Number(nonuniform[1])||cell>=values.length)throw Error(`Wrong field count/cell ${name}`);
    value=values[cell];
  }else throw Error(`Unsupported internal field ${name}`);
  if(!Number.isFinite(value))throw Error(`Nonfinite ${name}`);
  fields[name]={file,sha256:sha(raw),bytes:raw.length};return value;
}
const pressure_Pa=await scalar('p'),temperature_K=await scalar('T'),storedHs_J_kg=await scalar('h');
const massFractions={};for(const name of species)massFractions[name]=await scalar(name);
const massSum=Object.values(massFractions).reduce((a,b)=>a+b,0);
if(pressure_Pa<=0||temperature_K<=0||Math.abs(massSum-1)>1e-10||Object.values(massFractions).some(v=>v<0))throw Error('Invalid captured thermodynamic state; no normalization performed');
const point={schema:'captured-failed-thermo-point/v1',sourceCase:root,snapshotTime:time,rank,cell,pressure_Pa,temperature_K,storedHs_J_kg,species,massFractions,massSum,speciesNormalized:false,CFD_steps:0,authorizedForCFDRestart:false,thermoDictionarySha256:sha(dictionary),fields};
if(options['--out']){
  if(!process.env.SLURM_JOB_ID)throw Error('Saving point export requires an allocation');
  const output=path.resolve(options['--out']);if(output===root||output.startsWith(root+path.sep))throw Error('Never write into the retained source case');
  await writeFile(output,JSON.stringify(point,null,2)+'\n',{flag:'wx'});
}
console.log(JSON.stringify({readOnly:!options['--out'],...point},null,2));
