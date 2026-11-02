import {createReadStream} from 'node:fs';
import {stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';

export const prefixes=Object.freeze([
 'energyState','energyEquation','energyResidualAudit','fgmBounds','fgmAppliedSource',
 'thermoClosure','thermoPostPressureClosure','steadyFlamelet','steadyEndpointInput',
 'steadyEndpointRepresentation','fgmContinuityStage','fgmZRoundoffProjection',
]);
export const defaultLimits=Object.freeze({lineBytes:1024*1024,records:1500000,
 retainedBytes:512*1024*1024,markerBytes:4*1024*1024});
// Keep exact evidence for every current checker predicate, including refusals.
const marker=/FOAM FATAL|Floating point exception|Segmentation fault|MPI_ABORT|error:|Error:|Warning|warning|out of temperature range|FGM_DIMIX_POLICY|Selecting RAS turbulence model|Selecting RAS thermophysical transport model|closure=RAS-kEpsilon-delta-PDF-diagnostic|Solving for c,|fgmSourceStage |endpoint-coordinate rawZ=|policy=strict/;
const lifecycle=/^(?:Time =|ExecutionTime =|End\s*$)/;

export async function scanSolverLog(path, overrides={}) {
 const limits={...defaultLimits,...overrides};
 for(const [name,value] of Object.entries(limits))
  if(!(name in defaultLimits)||!Number.isSafeInteger(value)||value<1)throw Error(`Invalid log limit: ${name}`);
 const before=await stat(path),hash=createHash('sha256');
 const groups=Object.fromEntries(prefixes.map(name=>[name,[]]));
 const times=[],markers=[];let bytes=0,lineCount=0,recordCount=0,retainedBytes=0,markerBytes=0,pending=Buffer.alloc(0);
 function consume(lineBytes, terminated) {
  lineCount++;
  if(lineBytes.length>limits.lineBytes)throw Error(`Log line byte limit exceeded at ${lineCount}`);
  const line=lineBytes.toString('utf8').replace(/\r$/,'');
  const space=line.indexOf(' '),name=space<0?line:line.slice(0,space);
  if(Object.hasOwn(groups,name)&&space>=0){
   recordCount++;retainedBytes+=lineBytes.length;
   if(recordCount>limits.records||retainedBytes>limits.retainedBytes)throw Error(`Retained scientific-log bound exceeded at ${lineCount}`);
   groups[name].push({line:lineCount,raw:line});
  }
  const time=/^Time = (\S+)\s*$/.exec(line);
  if(time)times.push({line:lineCount,token:time[1],value:Number(time[1])});
  if(marker.test(line)||lifecycle.test(line)){
   markerBytes+=lineBytes.length+(terminated?1:0);
   if(markerBytes>limits.markerBytes)throw Error(`Log marker byte limit exceeded at ${lineCount}`);
   markers.push({line:lineCount,raw:line});
  }
 }
 for await(const chunk of createReadStream(path)){
  hash.update(chunk);bytes+=chunk.length;
  const joined=pending.length?Buffer.concat([pending,chunk]):chunk;
  let begin=0,newline;
  while((newline=joined.indexOf(10,begin))>=0){consume(joined.subarray(begin,newline),true);begin=newline+1;}
  pending=Buffer.from(joined.subarray(begin));
  if(pending.length>limits.lineBytes)throw Error(`Unterminated log line byte limit exceeded after ${lineCount}`);
 }
 if(pending.length)consume(pending,false);
 const after=await stat(path);
 if(before.size!==after.size||before.mtimeMs!==after.mtimeMs||bytes!==before.size)throw Error('Solver log changed during complete streaming read');
 const identity={schema:'complete-solver-log-stream/v1',path,sha256:hash.digest('hex'),bytes,
  completeRawRead:true,sourceStable:true,originalLines:lineCount,retainedRecords:recordCount,retainedRecordBytes:retainedBytes,
  markerBytes,limits,recordCounts:Object.fromEntries(prefixes.map(name=>[name,groups[name].length])),
  sourceLineMappings:Object.fromEntries(prefixes.map(name=>[name,groups[name].map(row=>row.line)])),
  markerSourceLines:markers.map(row=>row.line)};
 return {identity,groups,times,markerText:(markers[0]?.line>1?'\n':'')+markers.map(row=>row.raw).join('\n')+'\n',
  lines(prefix){const name=prefix.trim();if(!Object.hasOwn(groups,name))throw Error(`Unregistered scientific prefix: ${prefix}`);return groups[name].map(row=>row.raw);}};
}
