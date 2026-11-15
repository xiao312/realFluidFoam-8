// Append an explicitly labelled diagnostic. Never replace a primary comparison.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const [specFile,site,catalog,action]=process.argv.slice(2);
if(!specFile||!site||!catalog||![undefined,'--apply'].includes(action))throw Error('Use SPEC SITE CATALOG [--apply]');
const read=p=>fs.readFileSync(p,'utf8'),json=p=>JSON.parse(read(p));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const spec=json(specFile),data=JSON.parse(read(path.join(site,'data.js')).replace(/^export default /,'').replace(/;\s*$/,'')),central=json(catalog);
if(data.figures.length!==75||central.targets.length!==75||data.papers.length!==12)throw Error('Fixed ladder changed');
if(!spec.id||!spec.label||!spec.note||spec.scientificAcceptance!==false||!spec.targets?.length)throw Error('Explicit diagnostic specification required');
for(const list of [data.figures,central.targets])for(const id of spec.targets)if(!list.some(f=>f.id===id))throw Error('Missing target:'+id);
for(const [file,hash] of Object.entries(spec.inputSha256))if(sha(fs.readFileSync(file))!==hash)throw Error('Input changed:'+file);
const bundle=read(path.join(site,'argos.js'));
if(!bundle.includes('from"./data.js"'))throw Error('Unknown UI binding');
if(action!=='--apply'){console.log(JSON.stringify({readOnly:true,targets:spec.targets,primaryComparisonsChanged:false}));process.exit(0);}
const protectedFields=list=>JSON.stringify(list.map(({views,...f})=>f));
const before=[protectedFields(data.figures),protectedFields(central.targets)];
const backup=path.join(path.dirname(specFile),'ui-backup-'+new Date().toISOString().replace(/[:.]/g,'-'));fs.mkdirSync(backup);
for(const name of ['data.js','index.html','site-manifest.json'])fs.copyFileSync(path.join(site,name),path.join(backup,name));
fs.copyFileSync(catalog,path.join(backup,'catalog.json'));
const assets=[];
function asset(file){const bytes=fs.readFileSync(file),hash=sha(bytes),rel='assets/'+path.basename(file,path.extname(file)).replace(/[^A-Za-z0-9_-]/g,'-')+'-'+hash.slice(0,12)+path.extname(file);const dest=path.join(site,rel);if(fs.existsSync(dest)&&sha(fs.readFileSync(dest))!==hash)throw Error('Asset collision');fs.writeFileSync(dest,bytes);assets.push(rel);return{file:rel,sha256:hash};}
const image=asset(spec.image),evidence=asset(spec.evidence);
for(const list of [data.figures,central.targets])for(const id of spec.targets){const target=list.find(f=>f.id===id);target.views=[{id:spec.id,label:spec.label,image:image.file,image_sha256:image.sha256,data:evidence.file,data_sha256:evidence.sha256,note:spec.note,scientificAcceptance:false},...(target.views||[]).filter(v=>v.id!==spec.id)];}
if(before[0]!==protectedFields(data.figures)||before[1]!==protectedFields(central.targets))throw Error('Primary/catalogue data changed');
fs.writeFileSync(catalog,JSON.stringify(central,null,2)+'\n');
data.central_ladder.catalog_sha256=sha(fs.readFileSync(catalog));data.captured_at=new Date().toISOString();delete data.snapshot_sha256;data.snapshot_sha256=sha(JSON.stringify(data));
const serialized='export default '+JSON.stringify(data).replaceAll('<','\\u003c')+';\n',module='data-'+data.snapshot_sha256.slice(0,16)+'.js';
fs.writeFileSync(path.join(site,'data.js'),serialized);fs.writeFileSync(path.join(site,module),serialized);
const compiled=bundle.replace('from"./data.js"','from"./'+module+'"'),entry='argos-'+sha(compiled).slice(0,16)+'.js';
fs.writeFileSync(path.join(site,entry),compiled);fs.writeFileSync(path.join(site,'index.html'),read(path.join(site,'index.html')).replace(/src="argos(?:-[a-f0-9]+)?\.js"/,'src="'+entry+'"'));
const manifest=json(path.join(site,'site-manifest.json'));
for(const name of [...assets,'data.js',module,entry,'index.html'])manifest.files[name]=sha(fs.readFileSync(path.join(site,name)));
manifest.snapshot_sha256=data.snapshot_sha256;fs.writeFileSync(path.join(site,'site-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
const receipt={backup,targets:spec.targets,assets,primaryComparisonsChanged:false,scientificAcceptance:false};
fs.writeFileSync(specFile+'.import.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
