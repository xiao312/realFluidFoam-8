import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {scalarValues} from '../../mascotte-g2/direct-fgm/diagnostics.mjs';
const paths=process.argv.slice(2).map(p=>resolve(p));
if(paths.length!==2)throw Error('Use compare-steady.mjs BASELINE OPTIMIZED');
const m=JSON.parse(await readFile(`${paths[0]}/verification-input.json`));
const meta=JSON.parse(await readFile(`${paths[0]}/constant/steady-species.json`));
const fields=['T','p','rho','h','Ha','Z','c','U',...meta];
const failures=[],measurements=[],runs=[];
function vectors(raw){
 const uniform=/internalField\s+uniform\s+\(([^)]+)\)/.exec(raw);
 if(uniform)return uniform[1].trim().split(/\s+/).map(Number);
 const field=/internalField\s+nonuniform\s+List<vector>\s+\d+\s*\(([\s\S]*?)\)\s*;/.exec(raw);
 if(!field)throw Error('Unsupported vector field');
 return [...field[1].matchAll(/\(([^)]+)\)/g)].flatMap(x=>x[1].trim().split(/\s+/).map(Number));
}
function records(log,prefix){return log.split(/\r?\n/).filter(l=>l.startsWith(prefix+(prefix==='steadyFlamelet'?' t=':' '))).map(l=>Object.fromEntries([...l.matchAll(/(\w+)=([^\s]+)/g)].map(([,k,v])=>[k,Number.isFinite(Number(v))?Number(v):v])));}
for(const root of paths){
 const check=JSON.parse(await readFile(`${root}/steady-periodic-result.json`));
 if(!check.mechanicalCompletion)failures.push(`${root}: periodic checker failed`);
 const log=await readFile(`${root}/log.solver`,'utf8');
 const times=(await readdir(root)).filter(n=>Number.isFinite(Number(n))&&Number(n)>0).sort((a,b)=>Number(a)-Number(b));
 if(times.length!==4||Math.abs(Number(times.at(-1))-m.endTime)>1e-16)failures.push(`${root}: output times`);
 const histories=Object.fromEntries(['energyState','energyEquation','thermoClosure','thermoPostPressureClosure','steadyFlamelet'].map(p=>[p,records(log,p)]));
 if(Object.values(histories).some(rows=>!rows.length||rows.some(row=>Object.values(row).some(v=>typeof v==='string'&&/^[+-]?(nan|inf)/i.test(v)))))throw Error('Missing/nonfinite history');
 runs.push({root,times,histories});
}
if(JSON.stringify(runs[0].times)!==JSON.stringify(runs[1].times))throw Error('Different write times');
for(const time of ['0',...runs[0].times])for(const field of time==='0'?['Ha']:fields){
 const values=await Promise.all(paths.map(async root=>{const raw=await readFile(`${root}/${time}/${field}`,'utf8');return field==='U'?vectors(raw):scalarValues(raw,field);}));
 if(values[0].length!==values[1].length||values.some(v=>v.some(x=>!Number.isFinite(x))))throw Error('Invalid fields');
 const maximumAbsolute=Math.max(...values[0].map((x,i)=>Math.abs(x-values[1][i])));
 if(maximumAbsolute!==0)failures.push(`${time}/${field}: nonzero difference`);
 measurements.push({time,field,maximumAbsolute});
}
for(const prefix of Object.keys(runs[0].histories)){
 if(JSON.stringify(runs[0].histories[prefix])!==JSON.stringify(runs[1].histories[prefix]))failures.push(`${prefix}: histories differ`);
 measurements.push({prefix,records:runs[0].histories[prefix].length,exactlyEqual:JSON.stringify(runs[0].histories[prefix])===JSON.stringify(runs[1].histories[prefix])});
}
const result={passed:!failures.length,failures,measurements,scientificAcceptance:false};
await writeFile(`${paths[1]}/steady-exact-parity.json`,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(result));if(!result.passed)process.exitCode=1;
