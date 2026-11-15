import fs from 'node:fs';
const root=process.argv[2],q=JSON.parse(fs.readFileSync(root+'/query.json')),rows=fs.readFileSync(root+'/cold-properties.csv','utf8').trim().split('\n'),keys=rows[0].split(','),v=Object.fromEntries(rows[1].split(',').map((s,i)=>[keys[i],Number(s)])),hc=v.Ha_J_kg-v.Hs_J_kg,target=q.storedHa_J_kg-hc;
if(!Number.isFinite(hc+target))throw Error('No executing-library formation basis');for(const n of ['cold-properties.csv','cold-inversion.csv'])fs.renameSync(root+'/'+n,root+'/initial-'+n);
fs.appendFileSync(root+'/constant/probeProperties',`\nenthalpyTargets (${target});targetGuesses (${q.temperature_K} ${q.tableTemperature_K} 300);targetCorrectionPasses 12;targetRelativeLimit 1e-8;\n`);
fs.writeFileSync(root+'/enthalpy-query-input.json',JSON.stringify({capturedHa_J_kg:q.storedHa_J_kg,libraryHchemical_J_kg:hc,targetHs_J_kg:target,compositionMode:q.compositionMode,CFDsteps:0,scientificAcceptance:false},null,2)+'\n');
