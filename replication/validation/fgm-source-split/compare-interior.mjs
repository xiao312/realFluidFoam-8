import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const [out,...cases]=process.argv.slice(2),hash=b=>createHash('sha256').update(b).digest('hex');
if(!out||cases.length!==4)throw Error('Use compare-interior.mjs NEW_REPORT CASE1 CASE2 CASE3 CASE4');
const groups=new Map(),identities={};
for(const path of cases){
 const raw=await readFile(`${path}/source-split-result.json`),r=JSON.parse(raw),m=r.input;
 identities[path]=hash(raw);
 if(m.kind!=='0d'||m.velocity!==0||m.startTime!==0||m.endTime!==1e-6||m.outer!==2||
    ![5e-9,1e-8].includes(m.dt)||m.thermodynamics?.equationOfState!=='soaveRedlichKwong')throw Error('Unexpected bounded interior case');
 const z=m.states[0].z;if(!m.states.every(s=>s.z===z&&s.c===m.states[0].c))throw Error('Expected uniform initial state');
 const group=groups.get(z)??[];group.push(r);groups.set(z,group);
}
if(groups.size!==2||[...groups.values()].some(g=>g.length!==2))throw Error('Require two Z values with two timesteps each');
const comparisons=[];
for(const[z,pair]of groups){
 const[fine,coarse]=pair.sort((a,b)=>a.input.dt-b.input.dt);
 if(fine.input.dt!==5e-9||coarse.input.dt!==1e-8||JSON.stringify(fine.input.inputHashes)!==JSON.stringify(coarse.input.inputHashes)||
    JSON.stringify(fine.input.states)!==JSON.stringify(coarse.input.states)||
    JSON.stringify(fine.input.progressSpecies)!==JSON.stringify(coarse.input.progressSpecies))throw Error('Paired physical inputs differ');
 const span=fine.input.states[0].cMax-fine.input.states[0].cMin;
 const differences=coarse.energy.map(row=>{
  const matches=fine.energy.filter(f=>Math.abs(f.t-row.t)<1e-15);
  if(matches.length!==1)throw Error('Missing or duplicate common time');
  return {time_s:row.t,coarseC:row.cmean,fineC:matches[0].cmean,differenceC:row.cmean-matches[0].cmean};
 });
 if(differences.length!==101||!(span>0))throw Error('Incomplete physical refinement history');
 const rms=Math.sqrt(differences.reduce((s,r)=>s+r.differenceC**2,0)/differences.length)/span;
 const limit=fine.input.thresholds.timestepCspanRms;
 if(limit!==coarse.input.thresholds.timestepCspanRms)throw Error('Paired criteria differ');
 comparisons.push({Z:z,Cspan:span,rms_Cspan:rms,max_Cspan:Math.max(...differences.map(r=>Math.abs(r.differenceC)))/span,
  limit_Cspan:limit,refinementPassed:Number.isFinite(rms)&&rms<=limit,
  bothCaseChecksPassed:fine.status==='pass'&&coarse.status==='pass',differences});
}
const result={schema:'fgm-interior-refinement/v1',caseResultHashes:identities,comparisons,
 mechanicalAndRefinementPassed:comparisons.every(r=>r.bothCaseChecksPassed&&r.refinementPassed),
 scientificAcceptance:false,globalCoverageQualified:false,interpretation:'Only two interior0D states; rich caps, manifold fidelity and independentODE confidence remain separate.'};
await writeFile(out,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({mechanicalAndRefinementPassed:result.mechanicalAndRefinementPassed,comparisons:comparisons.map(({differences,...r})=>r)}));
if(!result.mechanicalAndRefinementPassed)process.exitCode=1;
