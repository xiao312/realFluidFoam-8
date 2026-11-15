import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const [rawRoot,rawSite,rawCatalog,action]=process.argv.slice(2);
if(!rawRoot||!rawSite||!rawCatalog||![undefined,'--apply'].includes(action))throw Error('Use RESULTS_ROOT SITE CATALOG [--apply]');
const root=path.resolve(rawRoot),site=path.resolve(rawSite),catalog=path.resolve(rawCatalog),apply=action==='--apply';
const read=p=>fs.readFileSync(p,'utf8'),json=p=>JSON.parse(read(p)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const data=JSON.parse(read(path.join(site,'data.js')).replace(/^export default /,'').replace(/;\s*$/,'')),central=json(catalog);
const fieldRoot=path.resolve(json(path.join(root,'latest-short-field-review.json')).directory);
if(!fieldRoot.startsWith(root+path.sep))throw Error('Field root escapes investigation');
if(data.figures.length!==75||central.target_ids.length!==75||data.papers.length!==12)throw Error('Unexpected fixed catalogue');
const bindings={
 'schmitt2020-fig-21':'schmitt','muller2015-fig6a-temperature-field':'schmitt',
 'cavalieri2025-fig-6':'cavalieri','sharma2023-fig-4b':'cavalieri',
 'cavalieri2025-fig10a-tf-temperature-field':'cavalieri'
};
const protectedFields=list=>JSON.stringify(list.map(({views,...f})=>f));
const protectedUI=protectedFields(data.figures),protectedCentral=protectedFields(central.targets);
const bundle=read(path.join(site,'argos.js'));
if(!bundle.includes('from"./data.js"')||!read(path.join(site,'index.html')).match(/src="argos(?:-[a-f0-9]+)?\.js"/))throw Error('Unknown UI bindings');
for(const id of Object.keys(bindings))if(!data.figures.some(f=>f.id===id)||!central.targets.some(f=>f.id===id))throw Error('Target missing:'+id);
for(const f of ['investigation-report.md','hot-enthalpy-query-summary.json','new-cold-conserved-state-audit.json','hot-cell-source-diagnostic.png'])fs.accessSync(path.join(root,f));
for(const c of ['schmitt','cavalieri'])fs.accessSync(path.join(fieldRoot,c+'-source-clock-short-controls.png'));
if(!apply){console.log(JSON.stringify({readOnly:true,targets:75,papers:12,updatedViews:Object.keys(bindings),primaryComparisonsChanged:false,scientificAcceptance:false}));process.exit(0);}
const backup=path.join(root,'before-ui-import-'+new Date().toISOString().replace(/[:.]/g,'-'));fs.mkdirSync(backup);
for(const n of ['data.js','index.html','site-manifest.json'])fs.copyFileSync(path.join(site,n),path.join(backup,n));fs.copyFileSync(catalog,path.join(backup,'catalog.json'));
const assets=[];
function asset(file){const b=fs.readFileSync(file),hash=sha(b),stem=path.basename(file,path.extname(file)).replace(/[^A-Za-z0-9_-]/g,'-'),rel='assets/'+stem+'-'+hash.slice(0,12)+path.extname(file);const dest=path.join(site,rel);if(fs.existsSync(dest)&&sha(fs.readFileSync(dest))!==hash)throw Error('Asset collision');fs.writeFileSync(dest,b);assets.push(rel);return{file:rel,sha256:hash};}
const report=asset(path.join(root,'investigation-report.md'));
const evidence={kind:'source-clock-and-thermodynamic-coupling-investigation',scientificAcceptance:false,report,
 fields:asset(path.join(fieldRoot,'collection.json')),fieldArchive:asset(path.join(fieldRoot,'temperature-fields.tar.gz')),
 hotCellQueries:asset(path.join(root,'hot-enthalpy-query-summary.json')),conservedStateAudit:asset(path.join(root,'new-cold-conserved-state-audit.json')),
 hotCellFigure:asset(path.join(root,'hot-cell-source-diagnostic.png')),
 sourceClockCFD:'d020b8df0d7ba6c9fd2306770bb08f08d5292773',APIProbeSource:'6a9a2acd725c8b381f8b807efb3bf02ed7408c7e',candidateSource:'4e1a6acf88bb7b74799373018d5eb8df4bf63ee6',candidateCFDQualified:false};
fs.writeFileSync(path.join(root,'site-investigation-evidence.json'),JSON.stringify(evidence,null,2)+'\n');const ev=asset(path.join(root,'site-investigation-evidence.json'));
const images=Object.fromEntries(['schmitt','cavalieri'].map(c=>[c,asset(path.join(fieldRoot,c+'-source-clock-short-controls.png'))]));
for(const list of [data.figures,central.targets])for(const[id,c]of Object.entries(bindings)){
 const target=list.find(f=>f.id===id),im=images[c];
 const view={id:'source-clock-controls-20261115',label:c==='schmitt'?'Source-clock controls — same-time 300 µs':'Source-clock controls — failed faster-source state',image:im.file,image_sha256:im.sha256,data:ev.file,data_sha256:ev.sha256,
 note:c==='schmitt'?'Original-zero Schmitt job128102962: both300µs cases completed. Peak1689K→3254K with fixed10µs relaxation. Startup control; developed statistics and conservation acceptance remain open.':'Cavalieri job128103070: Cr100 control completed300µs; fixed10µs case failed caloric closure at161.809µs. Unequal times; hotter failed field is retained without acceptance.',scientificAcceptance:false};
 target.views=[...(target.views??[]).filter(v=>v.id!==view.id),view];
}
if(protectedFields(data.figures)!==protectedUI||protectedFields(central.targets)!==protectedCentral)throw Error('Protected target data changed');
fs.writeFileSync(catalog,JSON.stringify(central,null,2)+'\n');data.central_ladder.catalog_sha256=sha(fs.readFileSync(catalog));data.captured_at=new Date().toISOString();delete data.snapshot_sha256;data.snapshot_sha256=sha(JSON.stringify(data));
const serialized='export default '+JSON.stringify(data).replaceAll('<','\\u003c')+';\n',module='data-'+data.snapshot_sha256.slice(0,16)+'.js';fs.writeFileSync(path.join(site,'data.js'),serialized);fs.writeFileSync(path.join(site,module),serialized);
const compiled=bundle.replace('from"./data.js"','from"./'+module+'"'),entry='argos-'+sha(compiled).slice(0,16)+'.js';fs.writeFileSync(path.join(site,entry),compiled);fs.writeFileSync(path.join(site,'index.html'),read(path.join(site,'index.html')).replace(/src="argos(?:-[a-f0-9]+)?\.js"/,'src="'+entry+'"'));
const manifest=json(path.join(site,'site-manifest.json'));for(const name of [...assets,'data.js',module,entry,'index.html'])manifest.files[name]=sha(fs.readFileSync(path.join(site,name)));manifest.snapshot_sha256=data.snapshot_sha256;fs.writeFileSync(path.join(site,'site-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
fs.writeFileSync(path.join(root,'ui-import-receipt.json'),JSON.stringify({backup,targets:75,papers:12,updatedTargets:Object.keys(bindings),assets,evidence:ev,primaryComparisonsChanged:false,scientificAcceptance:false},null,2)+'\n');console.log(JSON.stringify({backup,targets:75,updatedTargets:Object.keys(bindings),assets:assets.length,scientificAcceptance:false}));
