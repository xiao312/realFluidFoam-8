import fs from 'node:fs';
import crypto from 'node:crypto';
import {dynamicLibraries} from './source-runtime-linkage.mjs';
const [build,input,parent]=process.argv.slice(2),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const q=JSON.parse(fs.readFileSync(parent+'/build-qualification.json')),source=JSON.parse(fs.readFileSync(input+'/source.json')),resolved=[];
for(const p of q.products)if(sha(fs.readFileSync(parent+'/'+p.file))!==p.sha256)throw Error('Parent changed:'+p.file);
for(const entry of dynamicLibraries(fs.readFileSync(build+'/logs/solver-ldd.txt','utf8'))){const p=q.products.find(p=>p.file==='lib/'+entry.name);if(!p)continue;if(fs.realpathSync(entry.path)!==fs.realpathSync(parent+'/'+p.file)||sha(fs.readFileSync(entry.path))!==p.sha256)throw Error('Mixed runtime:'+entry.name);resolved.push(entry.name);}
if([...resolved].sort().join()!==[...q.linkage].sort().join())throw Error('Linkage differs from S13');
const products=q.products.filter(p=>p.file!=='bin/reactingFoamSolveZ').map(p=>({...p,reused:true}));
products.push({file:'bin/reactingFoamSolveZ',sha256:sha(fs.readFileSync(build+'/bin/reactingFoamSolveZ')),reused:false});
const result={source:source.source,sourceArchiveSha256:source.archiveSha256,parentSource:q.source,parentRuntimeReceiptSha256:sha(fs.readFileSync(parent+'/build-qualification.json')),solverSha256:products.at(-1).sha256,custom_library_count:15,allCustomLibrariesRebuilt:false,compile_link_help_passed:true,products,linkage:q.linkage,resolvedLibraries:resolved,job:process.env.SLURM_JOB_ID,diagnosticDefault:false,CFDstepsAtBuild:0,scientificAcceptance:false};
fs.writeFileSync(build+'/build-qualification.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
