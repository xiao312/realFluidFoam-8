import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';

const options={},args=process.argv.slice(2);
for(let i=0;i<args.length;i+=2){
  if(!['--base-manifest','--transport','--out'].includes(args[i])||!args[i+1])
    throw Error('Use --base-manifest ORIGINAL_JSON --transport KONG_CHEMKIN [--out NEW_DIR]');
  options[args[i].slice(2)]=resolve(args[i+1]);
}
if(!options['base-manifest']||!options.transport)throw Error('Base manifest and transport input required');
const hash=b=>createHash('sha256').update(b).digest('hex');
const baseRaw=await readFile(options['base-manifest']),transportRaw=await readFile(options.transport);
const base=JSON.parse(baseRaw),keys=['Tc','Pc','Vc','omega','kappai','miui','sigmvi'];
if(base.schema!=='direct-realfluid-thermo-v1'||!Array.isArray(base.species))throw Error('Identified base thermo manifest required');
const parameters=new Map();
for(const s of base.species){
  if(parameters.has(s.name)||keys.some(k=>!Number.isFinite(s.dataForRealGas?.[k])))throw Error(`Invalid base species ${s.name}`);
  parameters.set(s.name,s.dataForRealGas);
}
if(parameters.has('CH3O2'))throw Error('Base already defines CH3O2; do not replace it');
const rows=transportRaw.toString().split(/\r?\n/).map(line=>line.split('!')[0].trim().split(/\s+/))
  .filter(row=>row[0]==='CH3O2');
if(rows.length!==1||rows[0].length!==7)throw Error('One complete CH3O2 Chemkin transport row required');
const [geometry,epsilon_K,sigma_A,dipole_D,polarizability_A3,rotationalRelaxation]=rows[0].slice(1).map(Number);
if(![geometry,epsilon_K,sigma_A,dipole_D,polarizability_A3,rotationalRelaxation].every(Number.isFinite)||epsilon_K<=0||sigma_A<=0)
  throw Error('Invalid dimensional CH3O2 transport inputs');
const NA=6.02214076e23,R=8.31446261815324;
const Tc=1.316*epsilon_K,Vc_m3_mol=3.29*NA*(sigma_A*1e-10)**3;
const Pc_Pa=R*Tc/(3*Vc_m3_mol);
const diffusionVolume=['C','H','O'].map(n=>parameters.get(n)?.sigmvi);
if(!diffusionVolume.every(v=>Number.isFinite(v)&&v>0))throw Error('Existing author C/H/O diffusion increments required');
const estimated={Tc,Pc:Pc_Pa/1e6,Vc:Vc_m3_mol*1e6,omega:0,kappai:0,miui:dipole_D,
  sigmvi:diffusionVolume[0]+3*diffusionVolume[1]+2*diffusionVolume[2]};
parameters.set('CH3O2',estimated);
const text=[...parameters].map(([name,p])=>`${name}\n{\n dataForRealGas { ${keys.map(k=>`${k} ${p[k]};`).join(' ')} }\n}\n`).join('\n');
const report={schema:'explicit-kong-radical-parameter-estimate/v1',base_manifest_sha256:hash(baseRaw),
  original_author_sha256:base.author_sha256,transport_sha256:hash(transportRaw),output_sha256:hash(text),
  existing_species_unchanged:base.species.length,estimated_species:['CH3O2'],dataForRealGas_CH3O2:estimated,
  transport_inputs:{epsilon_K,sigma_A,dipole_D,geometry,polarizability_A3,rotationalRelaxation},
  equations:{Tc:'1.316*(epsilon/kB)',Vc_m3_mol:'3.29*NA*sigma_m^3',Pc_Pa:'R*Tc/(3*Vc_m3_mol)',Zc:1/3},
  assumptions:['Spherical LJ proxy for chemically unstable CH3O2; omega=0 and association=0',
    'Fuller volume additive from retained C/H/O increments; no measured radical property claim'],
  references:['https://doi.org/10.1063/1.462271','https://shepherd.caltech.edu/EDL/publications/reprints/ShockDetonation.pdf'],
  kinetics_changed:false,scientific_acceptance:false};
if(options.out){await mkdir(options.out);await writeFile(`${options.out}/thermo.parameters`,text);
  await writeFile(`${options.out}/receipt.json`,JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify({readOnly:!options.out,...report},null,2));
