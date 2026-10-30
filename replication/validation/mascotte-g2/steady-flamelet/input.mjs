import {readFile} from 'node:fs/promises';
import {digest} from '../../fgm-of8/direct-verification/physical-input.mjs';

export async function loadSteadyTable(directory, metadataPath) {
  const [raw, receiptRaw, metadataRaw] = await Promise.all([
    readFile(`${directory}/steady.tbl`), readFile(`${directory}/manifest.json`), readFile(metadataPath)]);
  const receipt=JSON.parse(receiptRaw), metadata=JSON.parse(metadataRaw);
  if (receipt.schema!=='steady-flamelet-export/v1' || receipt.table_sha256!==digest(raw) ||
      receipt.metadata_sha256!==digest(metadataRaw) || receipt.mechanism_sha256!==metadata.mechanismSha256 ||
      receipt.composition_modified!==false || receipt.nodes_resampled!==false) throw Error('Steady physical input identity differs');
  const tokens=raw.toString().trim().split(/\s+/); let cursor=0;
  const key=k=>{if(tokens[cursor++]!==k)throw Error(`Expected ${k}`);};
  const number=()=>{const x=Number(tokens[cursor++]);if(!Number.isFinite(x))throw Error('Nonfinite/missing table value');return x;};
  const count=(lo,hi)=>{const x=number();if(!Number.isInteger(x)||x<lo||x>hi)throw Error('Invalid count');return x;};
  key('FORGE_STEADY_FLAMELET');if(number()!==1)throw Error('Unsupported steady table');
  key('pressure-pa');const pressure=number();key('chi-definition');const definition=tokens[cursor++];
  key('chi-value-s-1');const chi=number();key('oxidizer-temperature-k');const oxygenT=number();
  key('fuel-temperature-k');const fuelT=number();key('species');const ns=count(2,256), names=tokens.slice(cursor,cursor+=ns);
  key('elements');const ne=count(1,32), elements=tokens.slice(cursor,cursor+=ne);
  if(new Set(names).size!==ns||new Set(elements).size!==ne||!names.includes('CO')||!names.includes('CO2'))throw Error('Duplicate/missing species or element');
  if(JSON.stringify(names)!==JSON.stringify(metadata.species.map(s=>s.name))||JSON.stringify(names)!==JSON.stringify(receipt.species))throw Error('Thermo species order differs');
  if(pressure!==receipt.case.pressure_pa||chi!==receipt.chi_value_s_inverse||definition!==receipt.chi_definition||
    !['maximum','stoichiometric'].includes(definition)||!(pressure>0&&chi>0))throw Error('Condition/chi mismatch');
  key('element-mass-coefficients');const coefficients=Array.from({length:ne},()=>Array.from({length:ns},number));
  for(let e=0;e<ne;e++){
    const elemental=metadata.species.find(s=>Object.keys(s.composition).length===1&&s.composition[elements[e]]>0);
    if(!elemental)throw Error(`No elemental molecular-weight witness for ${elements[e]}`);
    const atomicWeight=elemental.molecularWeight_kg_kmol/elemental.composition[elements[e]];
    for(let s=0;s<ns;s++)if(Math.abs(coefficients[e][s]-atomicWeight*(metadata.species[s].composition[elements[e]]??0)/metadata.species[s].molecularWeight_kg_kmol)>1e-12)throw Error('Element coefficient differs from phase metadata');
  }
  key('points');const n=count(2,200000);key('data');
  const rows=Array.from({length:n},()=>({z:number(),temperature:number(),qFormation:number(),y:Array.from({length:ns},number)}));
  key('end');if(cursor!==tokens.length||rows[0].z!==0||rows.at(-1).z!==1)throw Error('Invalid end/Z endpoints');
  for(let i=0;i<n;i++){
    const row=rows[i];
    if((i&&row.z<=rows[i-1].z)||!(row.temperature>0)||row.y.some(y=>y<0||y>1+1e-8)||Math.abs(row.y.reduce((a,b)=>a+b)-1)>1e-8)throw Error(`Invalid species row ${i}`);
    for(const coefficient of coefficients){
      const dot=r=>r.y.reduce((a,y,s)=>a+y*coefficient[s],0);
      if(Math.abs(dot(row)-((1-row.z)*dot(rows[0])+row.z*dot(rows.at(-1))))>1e-8)throw Error(`Element balance fails at ${i}`);
    }
  }
  for(const [row,species,temp] of [[rows[0],'O2',oxygenT],[rows.at(-1),'CH4',fuelT]]){
    if(row.temperature!==temp||row.y.some((y,s)=>Math.abs(y-(names[s]===species?1:0))>1e-8))throw Error('Pure-stream endpoint differs');
  }
  const lookup=z=>{
    if(!Number.isFinite(z)||z<0||z>1)throw Error('Steady Z outside [0,1]; no clipping');
    let lo=0;while(lo<n-2&&rows[lo+1].z<z)lo++;
    const w=(z-rows[lo].z)/(rows[lo+1].z-rows[lo].z), lerp=(a,b)=>(1-w)*a+w*b;
    const y=names.map((_,s)=>lerp(rows[lo].y[s],rows[lo+1].y[s]));
    return{z,y,c:y[names.indexOf('CO2')]+y[names.indexOf('CO')],
      temperature:lerp(rows[lo].temperature,rows[lo+1].temperature),qFormation:lerp(rows[lo].qFormation,rows[lo+1].qFormation)};
  };
  return{raw,receipt,metadata,lookup,chi,chiDefinition:definition,inputHashes:{table:digest(raw),receipt:digest(receiptRaw),metadata:digest(metadataRaw),mechanism:metadata.mechanismSha256}};
}

export async function steadyInitialization(path,input){
  const raw=path?await readFile(path):null,config=raw?JSON.parse(raw):{mode:'uniform-steady',mixtureFraction:0};
  if(Object.keys(config).some(k=>!['mode','mixtureFraction'].includes(k))||config.mode!=='uniform-steady')throw Error('Steady closure requires explicit uniform-steady initialization, without eta/kernel');
  const state=input.lookup(config.mixtureFraction);
  return{config,sha256:raw?digest(raw):null,background:state,hot:state,
    interpretation:'Fresh uniform physical steady-table composition; c derived from Y only. Default Z=0 is cold pure oxygen, not an evolved CFD state.'};
}
