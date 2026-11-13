import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const args={};
for(let i=2;i<process.argv.length;i++){
  const key=process.argv[i];
  if(key==='--apply')args.apply=true;
  else if(['--site','--catalog','--comparison'].includes(key)&&process.argv[i+1])args[key.slice(2)]=path.resolve(process.argv[++i]);
  else throw Error(`Unknown or missing option ${key}`);
}
for(const key of ['site','catalog','comparison'])if(!args[key])throw Error(`Required --${key}`);
const read=p=>fs.readFileSync(p,'utf8');
const json=p=>JSON.parse(read(p));
const digest=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const writeJson=(p,value)=>fs.writeFileSync(p,JSON.stringify(value,null,2)+'\n');
const report=json(path.join(args.comparison,'comparison.json'));
assert.equal(report.schema,'maders-figure4-comparison/v1');
assert.equal(report.scientific_acceptance,false);
assert.match(report.job_id,/^\d+$/);
assert.match(report.source_commit,/^[a-f0-9]{40}$/);
for(const [name,hash] of Object.entries(report.artifacts)){
  assert.equal(path.basename(name),name);
  assert.equal(digest(fs.readFileSync(path.join(args.comparison,name))),hash);
}
for(const metric of report.metrics)
  assert.equal(digest(fs.readFileSync(metric.sample_file)),metric.sample_sha256,'Raw sample changed after plotting');
const dataFile=path.join(args.site,'data.js');
const payload=JSON.parse(read(dataFile).replace(/^export default /,'').replace(/;\s*$/,''));
const target=payload.figures.find(f=>f.id==='maders2017-fig-4');
assert.ok(target,'Existing registered Maders4 target required');
const others=payload.figures.filter(f=>f!==target).map(f=>JSON.stringify(f));
const central=json(args.catalog);
assert.ok(central.target_ids.includes(target.id));
if(!args.apply){
  console.log(JSON.stringify({plan:'Local preview import only; no approval or publication',target:target.id,job_id:report.job_id,time_s:report.sample_time_s,source_commit:report.source_commit,targets_preserved:payload.figures.length}));
  process.exit(0);
}
const stamp=new Date().toISOString();
const generation=digest(JSON.stringify(report));
const backup=path.join(args.site,'history');fs.mkdirSync(backup,{recursive:true});
const previous=digest(fs.readFileSync(dataFile));
if(!fs.existsSync(path.join(backup,previous+'.js')))fs.copyFileSync(dataFile,path.join(backup,previous+'.js'));
const asset=(source)=>{
  const bytes=fs.readFileSync(source),hash=digest(bytes),name=hash+path.extname(source);
  fs.writeFileSync(path.join(args.site,'assets',name),bytes);return {file:'assets/'+name,hash};
};
const image=asset(path.join(args.comparison,'figure4.svg'));
const data=asset(path.join(args.comparison,'comparison.json'));
const samples=[...new Set(report.metrics.map(m=>m.sample_file))].map(asset);
const history=report.time_history ? {
  image:asset(report.time_history.image_path),data:asset(report.time_history.data_path)
} : null;
const timeLabel=`${(1000*report.sample_time_s).toFixed(2)} ms`;
const temperatures=report.metrics.filter(m=>m.quantity==='T_K').map(m=>`H=${1000*m.height_m} mm: ${m.computed_max.toFixed(2)} K`).join('; ');
const failure=report.run_status?.state==='FAILED'
  ? ` Run failed at ${report.run_status.failure_time_s} s: ${report.run_status.reason}.` : '';
const note=`Transient CFD at ${report.sample_time_s} s, Slurm ${report.job_id}, source ${report.source_commit.slice(0,7)}. Paper: digitized Detailed–Verhoeven lines; ours: computed markers. ${temperatures}.${failure} Transient, mesh and model differences remain; no steady-state, independent review or scientific acceptance claimed.`;
Object.assign(target,{
  status:'review',result_image:image.file,result_image_sha256:image.hash,data:data.file,data_sha256:data.hash,note,
  views:[{id:'coflow-current',label:`OF8 FGM · transient ${timeLabel}`,image:image.file,image_sha256:image.hash,data:data.file,data_sha256:data.hash,note},
    ...(history?[{id:'coflow-time-history',label:'Profile history',image:history.image.file,image_sha256:history.image.hash,data:history.data.file,data_sha256:history.data.hash,note:'All saved profiles from this clean-start run; digitized-paper errors and evolution. No steady-state acceptance inferred.'}]:[])],
  development_state:{numerical:'pending',agent_review:'not_assessed',human_acceptance:'not_assessed'},
  review_generation:'sha256:'+generation,
  evidence_binding:{source:{executed_commit:report.source_commit},run:{job_id:report.job_id,sample_time_s:report.sample_time_s,clean_start_time_s:0,...(report.run_status?{terminal_status:report.run_status}:{})},artifacts:{comparison:data,raw_samples:samples},independent_review:null,human_acceptance:false}
});
assert.deepEqual(payload.figures.filter(f=>f!==target).map(f=>JSON.stringify(f)),others);
central.targets=central.targets.map(f=>f.id===target.id?structuredClone(target):f);
writeJson(args.catalog,central);
payload.central_ladder.catalog_sha256=digest(fs.readFileSync(args.catalog));
payload.captured_at=stamp;delete payload.snapshot_sha256;
payload.snapshot_sha256=digest(JSON.stringify(payload));
fs.writeFileSync(dataFile,'export default '+JSON.stringify(payload).replaceAll('<','\\u003c')+';\n');
const dataName=`data-${payload.snapshot_sha256.slice(0,16)}.js`;fs.copyFileSync(dataFile,path.join(args.site,dataName));
const bundle=read(path.join(args.site,'argos.js')).replace('from"./data.js"',`from"./${dataName}"`);
assert.ok(bundle.includes(dataName),'Actual Argos data import required');
const bundleName=`argos-${digest(bundle).slice(0,16)}.js`;fs.writeFileSync(path.join(args.site,bundleName),bundle);
const index=path.join(args.site,'index.html');fs.writeFileSync(index,read(index).replace(/src="argos(?:-[a-f0-9]+)?\.js"/,`src="${bundleName}"`));
const manifestFile=path.join(args.site,'site-manifest.json'),manifest=json(manifestFile);
for(const name of ['data.js',dataName,bundleName,'index.html',image.file,data.file,...samples.map(s=>s.file),...(history?[history.image.file,history.data.file]:[])])manifest.files[name]=digest(fs.readFileSync(path.join(args.site,name)));
manifest.snapshot_sha256=payload.snapshot_sha256;writeJson(manifestFile,manifest);
const receipt={importer_sha256:digest(fs.readFileSync(new URL(import.meta.url))),captured_at:stamp,target:target.id,generation,job_id:report.job_id,sample_time_s:report.sample_time_s,targets:payload.figures.length,papers:payload.papers.length,previous_payload_sha256:previous,snapshot_sha256:payload.snapshot_sha256,scientific_acceptance:false,independent_review:null,remote_operations:false};
writeJson(path.join(args.site,'maders-comparison-import-receipt.json'),receipt);console.log(JSON.stringify(receipt));
