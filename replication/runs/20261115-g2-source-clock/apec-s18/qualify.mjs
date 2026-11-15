import fs from 'node:fs';import crypto from 'node:crypto';import{dynamicLibraries}from './source-runtime-linkage.mjs';
const[build,parent,input]=process.argv.slice(2),sha=x=>crypto.createHash('sha256').update(x).digest('hex'),q=JSON.parse(fs.readFileSync(parent+'/build-qualification.json')),source=JSON.parse(fs.readFileSync(input+'/source.json'));
const libraries=q.products.filter(p=>p.file.startsWith('lib/'));
for(const p of libraries)if(sha(fs.readFileSync(build+'/'+p.file))!==p.sha256)throw Error('Library changed:'+p.file);
const products=[];
for(const app of ['realFluidContactAPEC','initializeSchmittContact']){
 const linkage=dynamicLibraries(fs.readFileSync(build+'/logs/'+app+'-ldd.txt','utf8'));
 for(const e of linkage){const p=libraries.find(p=>p.file==='lib/'+e.name);if(p&&sha(fs.readFileSync(e.path))!==p.sha256)throw Error('Wrong linked library:'+e.name);}
 if(!['libspecie.so','libreactionThermophysicalModels.so'].every(n=>linkage.some(e=>e.name===n)))throw Error('Missing custom thermo linkage');
 products.push({file:'bin/'+app,sha256:sha(fs.readFileSync(build+'/bin/'+app)),linkage});
}
console.log(JSON.stringify({source:source.source,parentSource:q.source,compileLinkHelpPassed:true,libraries,products,CFDfieldsReused:false,scientificAcceptance:false},null,2));
