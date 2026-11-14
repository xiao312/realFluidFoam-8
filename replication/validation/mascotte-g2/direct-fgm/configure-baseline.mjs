import {readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const [root,action]=process.argv.slice(2);
if(!root||![undefined,'--apply'].includes(action))throw Error('Use NEW_CASE [--apply]; default read-only');
const sha=x=>createHash('sha256').update(x).digest('hex');
const raw=await readFile(`${root}/direct-g2-input.json`),m=JSON.parse(raw);
if(m.startTime!==0||m.closure!=='steady-flamelet'||!m.skipUnusedDiffusion||m.energyForm!=='absoluteEnthalpy')throw Error('Fresh declared steady-flamelet absolute-Ha case required');
if((await readdir(root)).some(n=>/^processor/.test(n)||(Number.isFinite(Number(n))&&Number(n)>0)))throw Error('No decomposed or evolved case permitted');
const path=`${root}/system/controlDict`,before=await readFile(path);
if(/projectTabulatedZRoundoff|fgmThermoCorrectionPasses/.test(before))throw Error('Baseline already configured');
const densityFlags=[...before.toString().matchAll(/\bconserveTabulatedDensity\s+(yes|no)\s*;/g)];
if(densityFlags.length>1||(densityFlags.length===1&&densityFlags[0][1]!=='yes'))throw Error('Conflicting conservative-density selection');
const text=before.toString().replace(/runTimeModifiable\s+no\s*;/,'runTimeModifiable yes;')+
 '\nwriteMixtureFractionBudget yes;\nwriteFgmTiming yes;\n'+(densityFlags.length?'':'conserveTabulatedDensity yes;\n')+
 'projectTabulatedZRoundoff yes;\nfgmThermoCorrectionPasses 3;\n';
const receipt={schema:'parallel-g2-baseline-controls/v1',case:root,startTime_s:0,
 controlBeforeSha256:sha(before),controlAfterSha256:sha(text),manifestBeforeSha256:sha(raw),
 energy:'absoluteHa,unchanged stored h during three inversion passes',lookup:'endpoint64epsilon',
 acceptanceLimitChanged:false,fieldValuesChanged:false,operationalStopEnabled:true,
 averaging:'retain instantaneous profiles; offline time-weighted statistics over declared actual window',scientificAcceptance:false};
if(!action){console.log(JSON.stringify({readOnly:true,...receipt},null,2));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Allocated execution required');
m.parallelBaseline=receipt;
await writeFile(path,text);await writeFile(`${root}/direct-g2-input.json`,JSON.stringify(m,null,2)+'\n');
await writeFile(`${root}/baseline-controls.json`,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(receipt,null,2));
