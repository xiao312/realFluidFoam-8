import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {withInertSpecies} from './inert-species.mjs';

const [build, thermo, table, root, rawCr, action] = process.argv.slice(2);
const Cr = Number(rawCr), apply = action === '--apply';
if (![build,thermo,table,root].every(p => p && path.isAbsolute(p))
    || ![1,100].includes(Cr) || ![undefined,'--apply'].includes(action)
    || fs.existsSync(root)) throw Error('Use BUILD THERMO TABLE NEW_CASE 1|100 [--apply]');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const dictionary = fs.readFileSync(thermo+'/thermophysicalProperties','utf8');
const metadata = JSON.parse(fs.readFileSync(thermo+'/manifest.json'));
const tableBytes = fs.readFileSync(table);
if (metadata.species.length !== 53) throw Error('Full53 original thermo required');
const activeDictionary = withInertSpecies(dictionary, 'O2');
const record = {schema:'relaxed-table-source-control/v1',Cr,Z:0.2,T_K:300,p_Pa:5600000,
  CFDsteps:0,physicalTime:0,actualComposition:'CH4=.2,O2=.8,others=0',
  inertBookkeeping:'O2; coefficients unchanged',
  originalThermoSha256:sha(dictionary),tableSha256:sha(tableBytes),
  buildQualificationSha256:sha(fs.readFileSync(build+'/build-qualification.json')),
  scientificAcceptance:false};
if (!apply) {console.log(JSON.stringify({readOnly:true,...record},null,2));process.exit(0);}
if (!process.env.SLURM_JOB_ID) throw Error('Apply requires Slurm');
const factory=build+'/source/replication/validation/realfluid-g2-thermo/probe/prepare.mjs';
const result=spawnSync('node',[factory,'--thermo-dir',thermo,'--species','O2','--out',root],{encoding:'utf8'});
if(result.status!==0)throw Error(result.stderr || result.error?.message || 'Probe factory failed');
fs.writeFileSync(root+'/factory-preparation.json',result.stdout);
fs.copyFileSync(root+'/initialization-input.json',root+'/factory-initialization-input.json');
const header=(object,cls='dictionary')=>`FoamFile {version 2.0;format ascii;class ${cls};object "${object}";}\n`;
const put=(name,text)=>fs.writeFileSync(root+'/'+name,text);
function scalar(name,dimensions,value){put('0/'+name,header(name,'volScalarField')+
  `dimensions [${dimensions}]; internalField uniform ${value}; boundaryField {walls {type zeroGradient;}}\n`);}
scalar('p','1 -1 -2 0 0 0 0',record.p_Pa);scalar('T','0 0 0 1 0 0 0',record.T_K);
scalar('Z','0 0 0 0 0 0 0',record.Z);
for(const species of metadata.species)scalar(species.name,'0 0 0 0 0 0 0',species.name==='CH4'?.2:species.name==='O2'?.8:0);
put('0/U',header('U','volVectorField')+'dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0); boundaryField {walls {type fixedValue;value uniform (0 0 0);}}\n');
put('constant/thermophysicalProperties',activeDictionary);
put('constant/steady.tbl',tableBytes);
put('constant/combustionProperties',header('combustionProperties')+`combustionModel relaxedTable; relaxedTableCoeffs {table "${root}/constant/steady.tbl";relaxationSteps ${Cr};lookupRoundoffPolicy endpoint64epsilon;}\n`);
put('constant/momentumTransport',header('momentumTransport')+'simulationType laminar;\n');
put('constant/thermophysicalTransport',header('thermophysicalTransport')+'simulationType laminar;laminar {model Fourier;}\n');
fs.appendFileSync(root+'/system/controlDict','\nfgmEnergyForm absoluteEnthalpy;fgmProgressSourceEnabled no;fgmSourceIntegration explicit;fgmSkipUnusedDimix yes;fgmRequireHaInitialization yes;writeFgmThermoClosure yes;relaxationProbeSteps 20;\n');
put('system/fvSolution',header('fvSolution')+'solvers {} PIMPLE {nOuterCorrectors 2;nCorrectors 2;nNonOrthogonalCorrectors 0;pRefCell 0;pRefValue 5600000;}\n');
put('active-source-control.json',JSON.stringify(record,null,2)+'\n');
console.log(JSON.stringify({created:root,...record},null,2));
