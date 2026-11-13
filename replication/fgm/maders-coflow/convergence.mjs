import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import crypto from 'node:crypto';

// These are provisional temporal-settling criteria, not paper-error tolerances.
export const criteria={minimum_time_s:2*.1/.23,check_interval_s:.05,lags_s:[.05,.1],
  maximum_T_change_K:10,maximum_CO_change:5e-4,consecutive_checks:3,expected_points:249};

export function screen(profiles,limits=criteria){
  const checks=[];let last=-Infinity,consecutive=0;
  for(const current of profiles){
    if(current.time_s<limits.minimum_time_s || current.time_s-last<limits.check_interval_s-.0025)continue;
    last=current.time_s;
    const comparisons=[];
    for(const lag of limits.lags_s){
      const candidates=profiles.filter(p=>p.time_s<current.time_s);
      const old=candidates.reduce((best,p)=>!best||Math.abs(p.time_s-(current.time_s-lag))<Math.abs(best.time_s-(current.time_s-lag))?p:best,null);
      if(!old||Math.abs(current.time_s-old.time_s-lag)>.006)continue;
      for(const height of ['h10','h40']){
        const now=current[height],before=old[height];
        if(now.length!==before.length)throw Error('Profile grid changed');
        let maxT=0,maxCO=0;
        for(let j=0;j<now.length;j++){
          if(Math.abs(now[j].r-before[j].r)>1e-12)throw Error('Profile coordinate changed');
          maxT=Math.max(maxT,Math.abs(now[j].T-before[j].T));
          maxCO=Math.max(maxCO,Math.abs(now[j].CO-before[j].CO));
        }
        comparisons.push({height,lag_s:current.time_s-old.time_s,max_T_change_K:maxT,max_CO_change:maxCO});
      }
    }
    const passed=comparisons.length===4&&comparisons.every(c=>c.max_T_change_K<=limits.maximum_T_change_K&&c.max_CO_change<=limits.maximum_CO_change);
    consecutive=passed?consecutive+1:0;
    checks.push({time_s:current.time_s,passed,consecutive,comparisons});
  }
  return {schema:'maders-temporal-screen/v1',criteria:limits,saved_profiles:profiles.length,
    latest_time_s:profiles.at(-1)?.time_s??null,provisionally_steady:consecutive>=limits.consecutive_checks,
    latest_checks:checks.slice(-5),scientific_acceptance:false,
    interpretation:'Time settling only. Always compare profiles with literature; passing this screen does not establish physical accuracy.'};
}

function readPlane(directory,prefix){
  const file=fs.readdirSync(directory).find(n=>n.startsWith(prefix+'_T_')&&n.endsWith('.csv'));
  if(!file)throw Error('Plane not written yet: '+prefix);
  const lines=fs.readFileSync(path.join(directory,file),'utf8').trim().split(/\r?\n/);
  const names=lines.shift().split(',');const t=names.indexOf('T'),co=names.indexOf('CO');
  if(t<0||co<0)throw Error('Missing temperature/CO fields');
  return lines.map(line=>{
    const values=line.split(',').map(Number),row={r:values[0],T:values[t],CO:values[co]};
    if(!Object.values(row).every(Number.isFinite))throw Error('Nonfinite or partial profile row');
    return row;
  });
}

export function literatureMetrics(profile,reference){
  if(!profile)return [];
  return reference.curves.map(curve=>{
    const rows=profile[curve.height_m===.01?'h10':'h40'],key=curve.quantity==='T_K'?'T':'CO';
    const errors=[];
    for(const point of curve.points){
      if(point.r_m<rows[0].r||point.r_m>rows.at(-1).r)continue;
      let i=0;while(i<rows.length-2&&rows[i+1].r<point.r_m)i++;
      const w=(point.r_m-rows[i].r)/(rows[i+1].r-rows[i].r);
      errors.push((1-w)*rows[i][key]+w*rows[i+1][key]-point.value);
    }
    return {height_m:curve.height_m,quantity:curve.quantity,covered:errors.length,
      total:curve.points.length,RMSE:errors.length?Math.sqrt(errors.reduce((sum,e)=>sum+e*e,0)/errors.length):null};
  });
}

function main(){
  const args={};
  for(let i=2;i<process.argv.length;i++){
    if(['--plan','--watch','--stop-on-screen'].includes(process.argv[i]))args[process.argv[i].slice(2)]=true;
    else if(['--samples','--out','--control-dict','--reference','--solver-log'].includes(process.argv[i]))args[process.argv[i].slice(2)]=path.resolve(process.argv[++i]);
    else throw Error('Unknown monitor option');
  }
  if(!args.samples||!args.out)throw Error('Use --samples RADIAL_DIRECTORY --out RECEIPT [--plan|--watch]');
  if(args['stop-on-screen']&&(!args.watch||!args['control-dict']))throw Error('Stopping needs --watch and an explicit --control-dict');
  if(args.plan){console.log(JSON.stringify({plan:true,...args,criteria}));return;}
  const cache=new Map();
  const update=()=>{
    const warnings=[];
    for(const name of fs.existsSync(args.samples)?fs.readdirSync(args.samples):[]){
      if(!/^\d+(?:\.\d+)?(?:e[+-]?\d+)?$/i.test(name)||cache.has(name))continue;
      try{
        const directory=path.join(args.samples,name),h10=readPlane(directory,'h10'),h40=readPlane(directory,'h40');
        if(h10.length!==criteria.expected_points||h40.length!==criteria.expected_points)throw Error('Incomplete profile count');
        cache.set(name,{time_s:Number(name),h10,h40});
      }catch(error){warnings.push({time:name,message:error.message});}
    }
    const profiles=[...cache.values()].sort((a,b)=>a.time_s-b.time_s);
    const reference=args.reference?JSON.parse(fs.readFileSync(args.reference,'utf8')):null;
    const report={...screen(profiles),warnings,literature_metrics:reference?literatureMetrics(profiles.at(-1),reference):[],
      reference_sha256:reference?crypto.createHash('sha256').update(fs.readFileSync(args.reference)).digest('hex'):null,
      observed_at:new Date().toISOString(),monitor_sha256:crypto.createHash('sha256').update(fs.readFileSync(fileURLToPath(import.meta.url))).digest('hex')};
    if(args['solver-log']&&fs.existsSync(args['solver-log'])){
      const fd=fs.openSync(args['solver-log'],'r'),size=fs.fstatSync(fd).size,buffer=Buffer.alloc(Math.min(size,262144));
      try{fs.readSync(fd,buffer,0,buffer.length,size-buffer.length);}finally{fs.closeSync(fd);}
      const lines=buffer.toString('utf8').split(/\r?\n/),bounds={};
      for(const line of lines.filter(l=>l.startsWith('fgmSourceBounds '))){
        const fields=Object.fromEntries([...line.matchAll(/(\w+)=([^ ]+)/g)].map(m=>[m[1],Number.isFinite(Number(m[2]))?Number(m[2]):m[2]]));
        bounds[fields.stage]=fields;
      }
      report.latest_source_bounds=Object.values(bounds);
      report.latest_energy_state=lines.filter(l=>l.startsWith('fgmEnergyState ')).at(-1)??null;
      report.pressure_iteration_ceiling_hits_in_tail=lines.filter(l=>l.includes('Solving for p,')&&l.endsWith('No Iterations 200')).length;
    }
    fs.mkdirSync(path.dirname(args.out),{recursive:true});
    fs.writeFileSync(args.out+'.tmp',JSON.stringify(report,null,2)+'\n');fs.renameSync(args.out+'.tmp',args.out);
    if(args['stop-on-screen']&&report.provisionally_steady&&!warnings.length){
      const filename=args['control-dict'],text=fs.readFileSync(filename,'utf8');
      if(!/startFrom\s+startTime\s*;/.test(text)||!/startTime\s+0\s*;/.test(text))throw Error('Expected the declared clean-start case');
      const after=text.replace(/stopAt\s+endTime\s*;/,'stopAt writeNow;');
      if(after===text)throw Error('Expected stopAt endTime before graceful stop');
      fs.writeFileSync(filename+'.monitor-tmp',after);fs.renameSync(filename+'.monitor-tmp',filename);
      fs.writeFileSync(args.out+'.stop-receipt.json',JSON.stringify({time_s:report.latest_time_s,
        reason:'Provisional temporal screen; not science acceptance',before_sha256:crypto.createHash('sha256').update(text).digest('hex'),
        after_sha256:crypto.createHash('sha256').update(after).digest('hex')},null,2));
      console.log('TEMPORAL_SCREEN_STOP_REQUESTED time='+report.latest_time_s);return true;
    }
    return false;
  };
  if(update()||!args.watch)return;
  const timer=setInterval(()=>{try{if(update())clearInterval(timer);}catch(error){console.error('MONITOR_ERROR '+error.message);}},60000);
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main();
