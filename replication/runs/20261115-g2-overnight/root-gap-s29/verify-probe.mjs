import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {dynamicLibraries} from './source-runtime-linkage.mjs';
const parent='/workspace/build/relaxed-table-r54',build='/workspace/build/rho-ha-probe-s07',sha=b=>createHash('sha256').update(b).digest('hex');
const q=JSON.parse(fs.readFileSync(build+'/probe-qualification.json')),p=JSON.parse(fs.readFileSync(parent+'/build-qualification.json'));
if(q.source!=='6a9a2acd725c8b381f8b807efb3bf02ed7408c7e'||q.probeSha256!=='599c29fee8bd509f3b9b58700a1c04048fffd0dea719221e8c4ac5a41ae9156d'||!q.compileLinkHelp||p.source!=='51075d584e7a9bb12a85201b6dcc4eae55303b52')throw Error('Unexpected qualified probe/runtime');
if(sha(fs.readFileSync(build+'/bin/realFluidG2ThermoProbe'))!==q.probeSha256)throw Error('Probe changed');
for(const item of p.products)if(sha(fs.readFileSync(parent+'/'+item.file))!==item.sha256)throw Error('Parent changed:'+item.file);
const linked=spawnSync('ldd',[build+'/bin/realFluidG2ThermoProbe'],{encoding:'utf8'});if(linked.status!==0)throw Error('ldd failed');
for(const e of dynamicLibraries(linked.stdout)){const item=p.products.find(p=>p.file==='lib/'+e.name);if(item&&fs.realpathSync(e.path)!==fs.realpathSync(parent+'/'+item.file))throw Error('Mixed runtime:'+e.name);}
console.log(JSON.stringify({probe:q,parentSource:p.source,actualLinkage:linked.stdout,CFDsteps:0,scientificAcceptance:false},null,2));
