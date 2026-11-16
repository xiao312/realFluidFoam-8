import {readFile,mkdir,writeFile,copyFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const options={},args=process.argv.slice(2);
for(let i=0;i<args.length;i+=2){
  if(!['--from','--metadata','--out'].includes(args[i])||!args[i+1])throw Error('Use --from ORIGINAL_THERMO --metadata NEW_PHASE [--out NEW_THERMO]');
  options[args[i].slice(2)]=resolve(args[i+1]);
}
if(!options.from||!options.metadata)throw Error('Original thermo and new metadata are required');
const sha=b=>createHash('sha256').update(b).digest('hex');
const original=await readFile(`${options.from}/manifest.json`),phase=await readFile(options.metadata);
const dictionary=await readFile(`${options.from}/thermophysicalProperties`);
const old=JSON.parse(original),meta=JSON.parse(phase);
if(old.schema!=='direct-realfluid-thermo-v1'||meta.schema!=='cantera-nasa7-phase/v1'||
   old.mechanism_sha256!==meta.mechanismSha256||old.species.length!==meta.species.length)
  throw Error('Mechanism/thermo metadata identity differs');
for(let i=0;i<old.species.length;i++) {
  const a=old.species[i],b=meta.species[i];
  if(a.name!==b.name||a.molecularWeight_kg_kmol!==b.molecularWeight_kg_kmol||JSON.stringify(a.thermo)!==JSON.stringify(b.thermo))
    throw Error(`Actual thermo coefficients differ at species ${i}`);
}
const binding={schema:'unchanged-realfluid-thermo-metadata-binding/v1',
  original_manifest_sha256:sha(original),original_phase_sha256:old.phase_sha256,
  new_phase_sha256:sha(phase),dictionary_sha256:sha(dictionary),species:old.species.length,
  mechanism_sha256:meta.mechanismSha256,physical_coefficients_changed:false,runtime_qualified:false,
  scientific_acceptance:false};
if(options.out){
  await mkdir(options.out);
  await copyFile(`${options.from}/thermophysicalProperties`,`${options.out}/thermophysicalProperties`);
  await writeFile(`${options.out}/original-manifest.json`,original);
  await writeFile(`${options.out}/manifest.json`,JSON.stringify({...old,phase_sha256:sha(phase),metadata_binding:binding},null,2)+'\n');
  await writeFile(`${options.out}/metadata-binding.json`,JSON.stringify(binding,null,2)+'\n');
}
console.log(JSON.stringify({readOnly:!options.out,...binding},null,2));
