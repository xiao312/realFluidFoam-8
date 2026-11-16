import {mkdir,copyFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {readMesh,evidence,inspectInjectorMesh} from './mesh.mjs';

const options={},args=process.argv.slice(2);
for(let i=0;i<args.length;i+=2){
  if(!['--case','--logs','--out'].includes(args[i])||!args[i+1])throw Error('Use --case EXECUTED_CASE [--logs DIR] [--out NEW_ASSET]');
  options[args[i].slice(2)]=resolve(args[i+1]);
}
if(!options.case)throw Error('Missing executed mesh case');
const logs=options.logs??options.case;
const measured=await readMesh(`${options.case}/constant/polyMesh`);
const proof=await evidence(options.case,logs,'system/blockMeshDict');
const manifest={...measured,schema:'g2-tapered-injector-qualified-asset/v1',evidence:proof,
  qualification:'Executed mesh tools plus measured inlet/exit geometry; not reacting CFD or paper acceptance'};
if(options.out){
  await mkdir(options.out);await mkdir(`${options.out}/polyMesh`);
  await copyFile(`${options.case}/system/blockMeshDict`,`${options.out}/blockMeshDict`);
  await copyFile(`${options.case}/mesh-recipe.json`,`${options.out}/mesh-recipe.json`);
  for(const name of ['log.blockMesh','log.checkMesh'])await copyFile(`${logs}/${name}`,`${options.out}/${name}`);
  for(const file of measured.files)await copyFile(`${options.case}/constant/polyMesh/${file.name}`,`${options.out}/polyMesh/${file.name}`);
  await writeFile(`${options.out}/manifest.json`,JSON.stringify(manifest,null,2)+'\n');
  await inspectInjectorMesh(options.out);
}
console.log(JSON.stringify({readOnly:!options.out,...manifest},null,2));
