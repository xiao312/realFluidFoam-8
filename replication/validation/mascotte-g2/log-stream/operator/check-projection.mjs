import{scanSolverLog}from'../reader.mjs';
import{writeJson}from'../json.mjs';
const maximum=(values,seed=-Infinity)=>values.reduce((m,v)=>Math.max(m,v),seed);
import{readFile,writeFile}from'node:fs/promises';import{createHash}from'node:crypto';
const[root,mode]=process.argv.slice(2);if(!root||!['interior-off','interior-on','cold'].includes(mode))throw Error('Use CASE MODE');
const scanned=await scanSolverLog(`${root}/log.solver`),log=scanned.markerText,limit=64*Number.EPSILON;
const rows=prefix=>scanned.lines(prefix).map(l=>Object.fromEntries([...l.matchAll(/(\w+)=([^\s]+)/g)].map(([,k,v])=>[k,Number.isFinite(Number(v))?Number(v):v])));
const ledger=rows('fgmZRoundoffProjection'),stages=rows('fgmContinuityStage'),failures=[];const check=(v,m)=>{if(!v)failures.push(m);};
if(mode==='interior-off')check(ledger.length===0,'Default-off emitted projection records');
else check(ledger.length>0,'Projection ledger missing');
let signed=0,absolute=0,cells=0;
const keys=['t','beforeMinimum','beforeMaximum','afterMinimum','afterMaximum','cells','maxDelta','signedMassKg','absoluteMassKg','cumulativeSignedMassKg','cumulativeAbsoluteMassKg','cumulativeCells','limit','fieldsModified','oldTimeModified','prescribedBoundariesModified'];
for(const r of ledger){
 check(keys.every(k=>Number.isFinite(r[k])),'Nonfinite/missing ledger value');
 check(r.limit===limit&&r.maxDelta>=0&&r.maxDelta<=limit&&r.beforeMinimum>=-limit&&r.beforeMaximum<=1+limit&&r.afterMinimum>=-limit&&r.afterMaximum<=1+limit,'Fixed roundoff bound violated');
 check(Number.isInteger(r.cells)&&r.cells>=0&&r.absoluteMassKg>=0&&Math.abs(r.signedMassKg)<=r.absoluteMassKg*(1+8*Number.EPSILON),'Invalid mass correction/count');
 check(r.oldTimeModified===0&&r.prescribedBoundariesModified===0&&r.fieldsModified===(r.cells>0?1:0),'Unexpected field/history policy');
 signed+=r.signedMassKg;absolute+=r.absoluteMassKg;cells+=r.cells;
 const tolerance=32*Number.EPSILON*Math.max(absolute,Number.MIN_VALUE);
 check(Math.abs(r.cumulativeSignedMassKg-signed)<=tolerance&&Math.abs(r.cumulativeAbsoluteMassKg-absolute)<=tolerance&&r.cumulativeCells===cells,'Cumulative ledger arithmetic inconsistent');
 if(mode==='interior-on')check(r.cells===0&&r.maxDelta===0&&r.absoluteMassKg===0,'Interior pair unexpectedly needed a projection');
}
if(mode==='cold')check(cells>0,'Cold test did not exercise the policy');
const masses=stages.map(r=>r.massKg).filter(Number.isFinite),massMax=masses.length?maximum(masses):null;
const report={mode,passed:!failures.length,failures,records:ledger.length,projectedCellQueries:cells,cumulativeSignedMassKg:signed,cumulativeAbsoluteMassKg:absolute,
 maximumDelta:maximum(ledger.map(r=>r.maxDelta),0),fixedLimit:limit,
 cumulativeAbsoluteFractionOfMaximumObservedMass:massMax===null?null:absolute/massMax,
 cumulativeMassBoundEstimateKg:massMax===null?null:limit*massMax*ledger.length,
 boundEstimateDefinition:'64epsilon times maximum sampled stage mass times projection calls; not exact per-call mass and not an extra acceptance gate',
 logSha256:scanned.identity.sha256,logInputIdentity:scanned.identity,exactScalarConservationEstablished:false,scientificAcceptance:false};
await writeJson(`${root}/projection-ledger-result.json`,report);
console.log(JSON.stringify({passed:report.passed,failures,records:report.records,projectedCellQueries:cells,cumulativeAbsoluteMassKg:absolute,logSha256:report.logSha256}));if(!report.passed)process.exitCode=1;
