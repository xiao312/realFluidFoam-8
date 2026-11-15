import fs from 'node:fs';
const [root,mode]=process.argv.slice(2);
if(!['steps','fixedTime','exactCoarse','exactFine','legacyUnsupported','invalid'].includes(mode))throw Error('Unknown probe');
const file=root+'/constant/combustionProperties';
if(mode!=='steps')fs.writeFileSync(file,fs.readFileSync(file,'utf8').replace('relaxationSteps 100;',`relaxationMode ${mode==='fixedTime'?'fixedTime':'fixedTimeExact'};relaxationTime ${mode==='invalid'?0:100};`));
const control=root+'/system/controlDict';let text=fs.readFileSync(control,'utf8');
if(mode==='exactFine'){
 if(!/deltaT\s+1(?:\.0*)?\s*;/.test(text))throw Error('Expected original probe dt=1');
 text=text.replace(/deltaT\s+1(?:\.0*)?\s*;/,'deltaT 0.5;').replace('relaxationProbeSteps 20;','relaxationProbeSteps 40;');
}
fs.writeFileSync(control,text);
