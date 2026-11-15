import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const [rawRoot,rawSite,rawCatalog,action]=process.argv.slice(2);
if(!rawRoot||!rawSite||!rawCatalog||![undefined,'--apply'].includes(action))throw Error('Use ROOT SITE CATALOG [--apply]');
const root=path.resolve(rawRoot),site=path.resolve(rawSite),catalog=path.resolve(rawCatalog),apply=action==='--apply';
const read=p=>fs.readFileSync(p,'utf8'),json=p=>JSON.parse(read(p)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const data=JSON.parse(read(path.join(site,'data.js')).replace(/^export default /,'').replace(/;\s*$/,'')),central=json(catalog);
const fieldRoot=path.resolve(json(path.join(root,'latest-temporal-field-review.json')).directory);
const review=path.join(root,'s12-1ms-paper-review'),receipt=json(path.join(review,'receipt.json')),run=json(path.join(root,'s12-1ms-run-record.json'));
if(data.figures.length!==75||central.targets.length!==75||data.papers.length!==12||run.jobId!=='128109186'||run.solverExit!==0||run.sampleTime_s!==.001)throw Error('Unexpected identity/catalog');
for(const[file,hash]of Object.entries(receipt.input_hashes))if(sha(fs.readFileSync(file))!==hash)throw Error('Changed renderer input:'+file);
const protectedFields=list=>JSON.stringify(list.map(({views,...f})=>f));
const protectedUI=protectedFields(data.figures),protectedCentral=protectedFields(central.targets),bundle=read(path.join(site,'argos.js'));
const bindings={'cavalieri2025-fig-6':['cavalieri-15mm','cavalieri-45mm','cavalieri-70mm'],'sharma2023-fig-4b':['axial-instantaneous']};
if(!bundle.includes('from"./data.js"'))throw Error('Unknown UI binding');
if(!apply){console.log(JSON.stringify({readOnly:true,targets:75,papers:12,updatedViews:Object.keys(bindings),primaryComparisonsChanged:false,scientificAcceptance:false}));process.exit(0);}
const backup=path.join(root,'before-ui-import-'+new Date().toISOString().replace(/[:.]/g,'-'));fs.mkdirSync(backup);
for(const n of ['data.js','index.html','site-manifest.json'])fs.copyFileSync(path.join(site,n),path.join(backup,n));fs.copyFileSync(catalog,path.join(backup,'catalog.json'));
const assets=[];
function asset(file){const b=fs.readFileSync(file),hash=sha(b),stem=path.basename(file,path.extname(file)).replace(/[^A-Za-z0-9_-]/g,'-'),rel='assets/'+stem+'-'+hash.slice(0,12)+path.extname(file);const dest=path.join(site,rel);if(fs.existsSync(dest)&&sha(fs.readFileSync(dest))!==hash)throw Error('Asset collision');fs.writeFileSync(dest,b);assets.push(rel);return{file:rel,sha256:hash};}
if(sha(fs.readFileSync(run.runtimeReceiptFile))!==run.runtimeReceiptSha256)throw Error('Runtime receipt hash mismatch');
const artifacts=[asset(run.runtimeReceiptFile),asset(path.join(root,'s12-1ms-mass-audit.json')),asset(path.join(root,'s12-1ms-energy-audit.json')),asset(path.join(review,'receipt.json')),asset(path.join(root,'s12-1ms-run-record.json')),asset(path.join(root,'s12-1ms-collection.json')),asset(path.join(root,'temporal-status-1958.json')),asset(path.join(fieldRoot,'collection.json'))];
for(const name of fs.readdirSync(path.join(review,'data')))if(name.endsWith('.csv'))artifacts.push(asset(path.join(review,'data',name)));
const evidence={job:'128109186',source:run.source_commit,solverSha256:run.solver_sha256,startTime_s:0,time_s:.001,solverExit:0,Slurm:'COMPLETED',elapsed_s:5251,model:run.model,artifacts,scientificAcceptance:false,developedMeansAvailable:false};
const evidenceFile=path.join(root,'s12-site-evidence.json');fs.writeFileSync(evidenceFile,JSON.stringify(evidence,null,2)+'\n');const ev=asset(evidenceFile);
const note='Fresh-zero refined Cavalieri job128109186 completed1ms,5251s,solver0. Fixed10us Euler source,maxdt0.5us. Finalcaloric2.394e-9 passes unchanged1e-8; globalenergy/elements and papermeans notqualified. Tmax3323K is localized nearinjector,not radial-profile agreement; older5ms and failedcontrols retained.';
for(const list of [data.figures,central.targets]){
 for(const[id,names]of Object.entries(bindings)){
  const target=list.find(f=>f.id===id),views=names.map(name=>{const im=asset(path.join(review,name+'.png'));return{id:'s12-refined-1ms-'+name,label:'Refined source clock — 1 ms — '+name,image:im.file,image_sha256:im.sha256,data:ev.file,data_sha256:ev.sha256,note,scientificAcceptance:false};});
  target.views=[...views,...target.views.filter(v=>!v.id.startsWith('s12-refined-1ms-'))];
 }
}
const fieldImage=asset(path.join(fieldRoot,'cavalieri-temporal-1ms.png'));
for(const list of [data.figures,central.targets])for(const id of ['cavalieri2025-fig-6','sharma2023-fig-4b','cavalieri2025-fig10a-tf-temperature-field']){
 const target=list.find(f=>f.id===id),view={id:'s12-refined-1ms-field',label:'Refined source clock — actual 1 ms temperature field',image:fieldImage.file,image_sha256:fieldImage.sha256,data:ev.file,data_sha256:ev.sha256,note,scientificAcceptance:false};
 target.views=[...target.views.filter(v=>v.id!==view.id),view];
}
if(protectedFields(data.figures)!==protectedUI||protectedFields(central.targets)!==protectedCentral)throw Error('Protected target data changed');
fs.writeFileSync(catalog,JSON.stringify(central,null,2)+'\n');data.central_ladder.catalog_sha256=sha(fs.readFileSync(catalog));data.captured_at=new Date().toISOString();delete data.snapshot_sha256;data.snapshot_sha256=sha(JSON.stringify(data));
const serialized='export default '+JSON.stringify(data).replaceAll('<','\\u003c')+';\n',module='data-'+data.snapshot_sha256.slice(0,16)+'.js';fs.writeFileSync(path.join(site,'data.js'),serialized);fs.writeFileSync(path.join(site,module),serialized);
const compiled=bundle.replace('from"./data.js"','from"./'+module+'"'),entry='argos-'+sha(compiled).slice(0,16)+'.js';fs.writeFileSync(path.join(site,entry),compiled);fs.writeFileSync(path.join(site,'index.html'),read(path.join(site,'index.html')).replace(/src="argos(?:-[a-f0-9]+)?\.js"/,'src="'+entry+'"'));
const manifest=json(path.join(site,'site-manifest.json'));for(const name of [...assets,'data.js',module,entry,'index.html'])manifest.files[name]=sha(fs.readFileSync(path.join(site,name)));manifest.snapshot_sha256=data.snapshot_sha256;fs.writeFileSync(path.join(site,'site-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
fs.writeFileSync(path.join(root,'temporal-ui-import-receipt.json'),JSON.stringify({backup,targets:75,papers:12,updatedTargets:[...Object.keys(bindings),'cavalieri2025-fig10a-tf-temperature-field'],assets,evidence:ev,primaryComparisonsChanged:false,scientificAcceptance:false},null,2)+'\n');console.log(JSON.stringify({backup,targets:75,updatedTargets:[...Object.keys(bindings),'cavalieri2025-fig10a-tf-temperature-field'],assets:assets.length,scientificAcceptance:false}));
