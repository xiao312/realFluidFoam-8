import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root=process.argv[2],rows=[];
const custom=new Set(["ODE", "specie", "thermophysicalProperties", "chemistryModel", "solidThermo", "momentumTransportModels", "fluidThermoMomentumTransportModels", "thermophysicalTransportModels", "psiReactionThermophysicalTransportModels", "rhoReactionThermophysicalTransportModels", "radiationModels", "fvOptions", "fluidThermophysicalModels", "reactionThermophysicalModels", "combustionModels"]);
const selectedLibraryDirectory=process.env.FOAM_USER_LIBBIN;if(!selectedLibraryDirectory)throw Error('Explicit selected library directory required');
const modules=["src/ODE", "src/thermophysicalModels/specie", "src/thermophysicalModels/thermophysicalProperties", "src/thermophysicalModels/basic", "src/thermophysicalModels/reactionThermo", "src/thermophysicalModels/chemistryModel", "src/thermophysicalModels/solidThermo", "src/MomentumTransportModels/momentumTransportModels", "src/MomentumTransportModels/compressible", "src/ThermophysicalTransportModels", "src/ThermophysicalTransportModels/psiReactionThermo", "src/ThermophysicalTransportModels/rhoReactionThermo", "src/radiationModels", "src/combustionModels", "src/fvOptions", "applications/solvers/reactingFoamSolveZ", "replication/validation/realfluid-g2-thermo/probe", "replication/validation/schmitt-contact", "replication/validation/schmitt-contact/double-flux"];
const sha=x=>createHash('sha256').update(x).digest('hex');
for(const module of modules){
 const file=`${root}/${module}/Make/options`,before=readFileSync(file,'utf8');
 let text=before.replace(/\r\n/g,'\n');if(module.startsWith('src/')){if(!text.includes('EXE_INC ='))text='EXE_INC =\n'+text;if(!text.includes('LIB_LIBS ='))text+='\nLIB_LIBS =\n';}
 const linkKey=text.includes('EXE_LIBS =')?'EXE_LIBS =':'LIB_LIBS =';
 if(!text.includes('EXE_INC =')||!text.includes(linkKey))throw Error(file);
 text=text.replace('EXE_INC =','EXE_INC = -isystem "/usr/include/x86_64-linux-gnu" -B"/usr/lib/x86_64-linux-gnu/"');
 text=text.replace(linkKey,linkKey+' -B"/usr/lib/x86_64-linux-gnu/"');
 text=text.replace(/-l([A-Za-z0-9_]+)(?=\s|$)/g,(token,name)=>custom.has(name)?`\"${selectedLibraryDirectory}/lib${name}.so\"`:token);
 if([...text.matchAll(/-l([A-Za-z0-9_]+)(?=\s|$)/g)].some(m=>custom.has(m[1])))throw Error('Custom library search-order ambiguity');
 writeFileSync(file,text);rows.push({module,beforeSha256:sha(before),compiledSha256:sha(text),reason:'Qualified GCC11 multiarch include/link paths, quoted against wmake preprocessing'});
}
console.log(JSON.stringify(rows,null,2));
