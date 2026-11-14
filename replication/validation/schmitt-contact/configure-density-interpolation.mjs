import fs from 'node:fs';import crypto from 'node:crypto';
const[root,mode,action]=process.argv.slice(2);if(!root||!['linear','upwind'].includes(mode)||![undefined,'--apply'].includes(action))throw Error('Use NEW_CASE linear|upwind [--apply]');
if(fs.existsSync(root+'/initial-thermo.csv')||fs.readdirSync(root).some(n=>Number.isFinite(Number(n))&&Number(n)>0))throw Error('New uninitialized case required');
const file=root+'/system/fvSchemes',before=fs.readFileSync(file,'utf8');
if(!before.includes('interpolationSchemes { default linear; }')||before.includes('interpolate(rho)'))throw Error('Unexpected interpolation controls');
const after=mode==='linear'?before:before.replace('interpolationSchemes { default linear; }','interpolationSchemes { default linear; interpolate(rho) upwind phi; }');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex'),receipt={mode,beforeSHA256:sha(before),afterSHA256:sha(after),onlyNamedDensityInterpolationChanged:true,readOnly:!action,scientificAcceptance:false};
if(action){if(!process.env.SLURM_JOB_ID)throw Error('Allocated preparation required');fs.writeFileSync(file,after);fs.writeFileSync(root+'/density-interpolation-input.json',JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});}
console.log(JSON.stringify(receipt,null,2));
