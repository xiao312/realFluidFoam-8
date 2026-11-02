// Preserve parseSolverLog's exact values and original source line numbering.
export function conservationRecords(scanned){
 const result={states:[],equations:[],times:scanned.times,audits:[]};
 for(const row of result.times)if(!Number.isFinite(row.value))throw Error(`Nonfinite time on line ${row.line}`);
 const names={energyState:'states',energyEquation:'equations',energyResidualAudit:'audits'};
 for(const [name,key] of Object.entries(names))for(const row of scanned.groups[name]){
  const values=Object.fromEntries([...row.raw.matchAll(/(\w+)=([^\s]+)/g)].map(([,k,v])=>[k,Number(v)]));
  if(!Number.isFinite(values.t)||!Object.values(values).every(Number.isFinite))throw Error(`Malformed ${name} on line ${row.line}`);
  result[key].push({line:row.line,values,raw:row.raw});
 }
 return result;
}
