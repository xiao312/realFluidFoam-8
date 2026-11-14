import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const [directory,mode,action]=process.argv.slice(2);
if(!directory||!['uniform','interface'].includes(mode)||![undefined,'--apply'].includes(action))throw Error('Use CASE uniform|interface [--apply]');
const root=path.resolve(directory),raw=await readFile(`${root}/log.solver`),log=raw.toString(),input=JSON.parse(await readFile(`${root}/contact-double-flux.json`));
const parse=line=>Object.fromEntries([...line.matchAll(/([A-Za-z][A-Za-z0-9_]*)=([^\s]+)/g)].map(m=>[m[1],Number(m[2])]));
const initial=log.split('\n').find(l=>l.startsWith('CONTACT_DF_INIT ')),last=log.split('\n').filter(l=>l.startsWith('CONTACT_DF ')).at(-1),end=log.split('\n').find(l=>l.startsWith('CONTACT_DF_END '));
if(!initial||!last||!end||/FOAM FATAL|Floating point exception|Segmentation fault/.test(log))throw Error('Incomplete or failed DF case; retain its actual failure');
const start=parse(initial),result=parse(last),finished=parse(end);
const required=['t','pMin','pMax','uMin','uMax','rhoEOSrelative','cumulativeMassResidualKg','cumulativeEnergyDefectJ','cumulativeEnergyBalanceResidualJ'];
if(required.some(k=>!Number.isFinite(result[k]))||!Number.isFinite(start.massKg)||!Number.isFinite(start.absoluteEnergyJ))throw Error('Missing/nonfinite numerical witness');
if(Math.abs(finished.t-input.endTime_s)>1e-10*Math.max(1,input.endTime_s)||Math.abs(result.t-finished.t)>1e-10)throw Error('Requested end time not reached');
const equilibriumLimit=mode==='uniform'?1e-8:1e-6;
const metrics={pressureRelativeDeparture:Math.max(Math.abs(result.pMin-6e6),Math.abs(result.pMax-6e6))/6e6,velocityRelativeDeparture:Math.max(Math.abs(result.uMin-10),Math.abs(result.uMax-10))/10,
 massRelativeResidual:Math.abs(result.cumulativeMassResidualKg)/start.massKg,energyBudgetRelativeResidual:Math.abs(result.cumulativeEnergyBalanceResidualJ)/Math.max(1,Math.abs(start.absoluteEnergyJ)),
 energyDefectRelativeToInitial:Math.abs(result.cumulativeEnergyDefectJ)/Math.max(1,Math.abs(start.absoluteEnergyJ)),EOSDensityRelativeError:result.rhoEOSrelative};
const checks={completedTime:true,finite:true,pressureEquilibrium:metrics.pressureRelativeDeparture<=equilibriumLimit,velocityEquilibrium:metrics.velocityRelativeDeparture<=equilibriumLimit,massBalance:metrics.massRelativeResidual<=1e-8,energyAccounting:metrics.energyBudgetRelativeResidual<=1e-8,EOSDensity:metrics.EOSDensityRelativeError<=1e-8,uniformEnergyDefect:mode!=='uniform'||metrics.energyDefectRelativeToInitial<=1e-8};
const receipt={schema:'contact-double-flux-startup-check/v1',mode,sourceLogSha256:createHash('sha256').update(raw).digest('hex'),endTime_s:finished.t,checks,metrics,numericalStartupPassed:Object.values(checks).every(Boolean),scientificAcceptance:false,interpretation:'Numerical startup only; interface energy defect and paper profiles require separate review'};
if(action)await writeFile(`${root}/double-flux-startup-check.json`,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({readOnly:!action,...receipt},null,2));
if(!receipt.numericalStartupPassed)process.exitCode=3;
