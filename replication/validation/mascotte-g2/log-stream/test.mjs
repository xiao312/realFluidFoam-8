import {mkdir,writeFile,readFile,open} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {scanSolverLog} from './reader.mjs';
import {writeJson} from './json.mjs';
const [directory,...extra]=process.argv.slice(2);if(!directory||extra.length)throw Error('Use test.mjs NEW_FIXTURE_DIRECTORY');
const root=resolve(directory),here=dirname(fileURLToPath(import.meta.url));await mkdir(root);
const sample=`End\nignored\nenergyState t=NaN mass=bad\nTime = 1e-7\nFOAM FATAL ERROR\nendpoint-coordinate rawZ=1 policy=strict\n`;
await writeFile(`${root}/short.log`,sample);
const scanned=await scanSolverLog(`${root}/short.log`);
assert.equal(scanned.lines('energyState ')[0],'energyState t=NaN mass=bad');
assert.equal(scanned.groups.energyState[0].line,3);
assert.equal(/\nEnd\s*(?:\n|$)/.test(scanned.markerText),/\nEnd\s*(?:\n|$)/.test(sample));
assert.equal(scanned.markerText.includes('FOAM FATAL ERROR'),true);
await assert.rejects(scanSolverLog(`${root}/short.log`,{lineBytes:5}),/line byte limit/);
const value={finite:4,invalid:NaN,missing:undefined,rows:[1,undefined,Infinity,{label:'µ\nquoted"'}]};
await writeJson(`${root}/json.json`,value);
assert.equal(await readFile(`${root}/json.json`,'utf8'),JSON.stringify(value,null,2)+'\n');
// More records than V8's spread-argument limit; no physical result is implied.
const dimension=`${root}/dimension`;await mkdir(dimension);
const line='fgmZRoundoffProjection t=0 beforeMinimum=0 beforeMaximum=1 afterMinimum=0 afterMaximum=1 cells=0 maxDelta=0 signedMassKg=0 absoluteMassKg=0 cumulativeSignedMassKg=0 cumulativeAbsoluteMassKg=0 cumulativeCells=0 limit=1.4210854715202004e-14 fieldsModified=0 oldTimeModified=0 prescribedBoundariesModified=0\n';
const file=await open(`${dimension}/log.solver`,'wx');
try{for(let i=0;i<150;i++)await file.writeFile(line.repeat(1000));await file.writeFile(line);}finally{await file.close();}
const result=spawnSync(process.execPath,[`${here}/operator/check-projection.mjs`,dimension,'interior-on'],{encoding:'utf8',timeout:60000,maxBuffer:1024*1024});
assert.equal(result.status,0,result.stderr);
const report=JSON.parse(await readFile(`${dimension}/projection-ledger-result.json`));
assert.equal(report.records,150001);assert.equal(report.passed,true);
await assert.rejects(scanSolverLog(`${dimension}/log.solver`,{records:100}),/bound exceeded/);
await writeJson(`${root}/test-result.json`,{passed:true,invalidRawRecordPreserved:true,lineOneEndParity:true,
 fatalTextPreserved:true,explicitBoundsRefused:true,jsonPlainDataEqual:true,projectionDimensionRecords:150001,scientificAcceptance:false});
console.log(JSON.stringify({passed:true,projectionDimensionRecords:150001,scientificAcceptance:false}));
