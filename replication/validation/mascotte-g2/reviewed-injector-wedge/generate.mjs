import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { dictionary, header, plan } from './recipe.mjs';

const args=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){
  if(!['--out','--resolution'].includes(args[i])||!args[i+1]||options[args[i]])
    throw Error('Usage: generate.mjs [--resolution standard|debug-coarse] [--out NEW_CASE]');
  options[args[i]]=args[i+1];
}
const profile=options['--resolution']??'standard',receipt=plan(profile);
if(options['--out']) {
  const out=resolve(options['--out']);
  await mkdir(out); // Refuse an existing case, including one containing evolved fields.
  for(const directory of ['system','constant','0']) await mkdir(`${out}/${directory}`);
  await writeFile(`${out}/system/blockMeshDict`,dictionary(profile));
  await writeFile(`${out}/system/controlDict`,header('controlDict')+
    'application blockMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT .001; writeControl timeStep; writeInterval 1;\n');
  await writeFile(`${out}/system/fvSchemes`,header('fvSchemes')+
    'ddtSchemes { default Euler; } gradSchemes { default Gauss linear; } divSchemes { default none; } laplacianSchemes { default Gauss linear corrected; } interpolationSchemes { default linear; } snGradSchemes { default corrected; }\n');
  await writeFile(`${out}/system/fvSolution`,header('fvSolution')+'solvers {}\n');
  await writeFile(`${out}/mesh-recipe.json`,JSON.stringify(receipt,null,2)+'\n');
  receipt.output=out;
}
console.log(JSON.stringify(receipt,null,2));
