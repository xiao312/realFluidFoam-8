import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
const [root,mode,action]=process.argv.slice(2),apply=action==='--apply';
const pressures={p6000:6000000,p5610:5610000,p4994:4994379.4771387,p4869:4869192.4241113};
if(!root?.startsWith('/workspace/cases/oxygen-audit-s20-')||!(mode in pressures)||![undefined,'--apply'].includes(action)||fs.existsSync(root))throw Error('Fresh owned property case and known pressure required');
const temperatures=[...new Set([85,90,100,110,288,300,400,600,...Array.from({length:537},(_,i)=>117+i*.25),...Array.from({length:291},(_,i)=>141+i*.1),153.50257320852,154.29614934018])].sort((a,b)=>a-b);
const record={mode,pressure_Pa:pressures[mode],temperatureCount:temperatures.length,temperatureRange_K:[temperatures[0],temperatures.at(-1)],composition:'pure O2; all other52 species0',CFDsteps:0,scientificAcceptance:false};
if(!apply){console.log(JSON.stringify({readOnly:true,...record}));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw Error('Slurm required');
const factory='/workspace/build/relaxed-table-r54/source/replication/validation/realfluid-g2-thermo/probe/prepare.mjs';
const plan=spawnSync(process.execPath,[factory,'--thermo-dir','/workspace/results/g2-fixed-h-r42-schmitt/thermo','--species','O2'],{encoding:'utf8'});
if(plan.status!==0)throw Error(plan.stderr||plan.stdout);
const made=spawnSync(process.execPath,[factory,'--thermo-dir','/workspace/results/g2-fixed-h-r42-schmitt/thermo','--species','O2','--out',root],{encoding:'utf8'});
if(made.status!==0)throw Error(made.stderr||made.stdout);
fs.writeFileSync(root+'/factory-plan.json',plan.stdout);fs.writeFileSync(root+'/factory.json',made.stdout);
fs.writeFileSync(root+'/constant/probeProperties',`FoamFile {version 2.0;format ascii;class dictionary;object probeProperties;}\npressure ${pressures[mode]};temperatures (${temperatures.join(' ')});increments ();initialGuessOffset 0.5;writeSrkCoefficients yes;\n`);
fs.writeFileSync(root+'/query-input.json',JSON.stringify(record,null,2)+'\n');console.log(JSON.stringify({created:root,...record}));
