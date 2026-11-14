import {readFile,mkdir,writeFile,copyFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {solverSchemes} from '../fgm-of8/direct-verification/schemes.mjs';

const args=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){
  if(!['--thermo-dir','--kind','--nx','--out'].includes(args[i])||!args[i+1]||options[args[i]])throw Error('Use --thermo-dir DIR --kind oxygen|mixture --nx VALUE [--out NEW_CASE]');
  options[args[i]]=args[i+1];
}
const kind=options['--kind'],nx=Number(options['--nx']);
if(!['oxygen','mixture'].includes(kind)||!(kind==='oxygen'?[2,4,6]:[1e-5,2,4]).includes(nx))throw Error('Select a published kind/nx combination');
const raw=await readFile(`${options['--thermo-dir']}/thermophysicalProperties`);
const manifest=JSON.parse(await readFile(`${options['--thermo-dir']}/manifest.json`));
if(manifest.mixture!=='SRKchungTakaMixture'||JSON.stringify(manifest.species.map(s=>s.name))!==JSON.stringify(['H2','O2']))throw Error('Require exact H2/O2 SRK thermo export');
const sha=b=>createHash('sha256').update(b).digest('hex');
const plan={schema:'schmitt-contact/v1',kind,nx,pressure_Pa:6e6,velocity_m_s:10,dx_m:.01,cells:400,
  domain_m:[-2,2],endTime_s:.02,cleanStart_s:0,maximumTimeStep_s:5e-6,thermoCorrectionPasses:3,maximumTimeStep_s:5e-6,thermoCorrectionPasses:3,thermoSha256:sha(raw),source:'Schmitt2020 equations26/27,Figures5/6',
  limitations:['Own pressure-based algorithm, no AVBP conservative/nonconservative artificial viscosity','Domain length reconstructed from far-field isolation','Cryogenic NASA extrapolation remains unvalidated']};
if(!options['--out']){console.log(JSON.stringify(plan,null,2));process.exit(0);}
const out=resolve(options['--out']);await mkdir(out);
for(const d of ['0','constant','system'])await mkdir(`${out}/${d}`);
const header=(name,type='dictionary')=>`FoamFile { version 2.0; format ascii; class ${type}; object ${name}; }\n`;
const put=(name,text)=>writeFile(`${out}/${name}`,text);
await put('constant/thermophysicalProperties',raw);
await put('constant/combustionProperties',header('combustionProperties')+'combustionModel none;\n');
await put('constant/reactions',header('reactions')+'species (H2 O2); reactions {}\n');
await put('constant/momentumTransport',header('momentumTransport')+'simulationType laminar;\n');
await put('constant/thermophysicalTransport',header('thermophysicalTransport')+'laminar { model Fourier; }\n');
await put('constant/g',header('g','uniformDimensionedVectorField')+'dimensions [0 1 -2 0 0 0 0]; value (0 0 0);\n');
await put('constant/contactInput',header('contactInput')+`densityInversion ${kind==='oxygen'?'yes':'no'};\n`);
await put('system/blockMeshDict',header('blockMeshDict')+`convertToMeters 1;
vertices ((-2 0 0)(2 0 0)(2 .01 0)(-2 .01 0)(-2 0 .01)(2 0 .01)(2 .01 .01)(-2 .01 .01));
blocks (hex (0 1 2 3 4 5 6 7) (400 1 1) simpleGrading (1 1 1)); edges ();
boundary (left {type patch;faces ((0 4 7 3));} right {type patch;faces ((1 2 6 5));}
sides {type empty;faces ((0 1 5 4)(3 7 6 2)(0 3 2 1)(4 5 6 7));}); mergePatchPairs ();\n`);
// Abramowitz-Stegun erf approximation; preserve its formula/error in the receipt.
const erf=x=>{const sign=x<0?-1:1,t=1/(1+.3275911*Math.abs(x));return sign*(1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-.284496736)*t+.254829592)*t*Math.exp(-x*x));};
const cells=Array.from({length:400},(_,i)=>-2+(i+.5)*.01);
const oxygen=cells.map(x=>kind==='oxygen'?1:.5*(1-erf(Math.sqrt(6)*x/(nx*.01))));
const density=cells.map(x=>1000+.5*(100-1000)*(1+erf(Math.sqrt(6)*x/(nx*.01))));
const scalar=(name,dim,values,left,right)=>header(name,'volScalarField')+`dimensions ${dim};
internalField ${Array.isArray(values)?`nonuniform List<scalar> ${values.length} (\n${values.join('\n')}\n)`:`uniform ${values}`};
boundaryField {left {${left}} right {${right}} sides {type empty;}}\n`;
const inlet=value=>`type inletOutlet; inletValue uniform ${value}; value uniform ${value};`;
await put('0/T',scalar('T','[0 0 0 1 0 0 0]',100,inlet(100),inlet(100)));
await put('0/p',scalar('p','[1 -1 -2 0 0 0 0]',6e6,
 'type waveTransmissive; field p; psi thermo:psi; gamma 1.4; fieldInf 6000000; lInf 2; value uniform 6000000;',
 'type waveTransmissive; field p; psi thermo:psi; gamma 1.4; fieldInf 6000000; lInf 2; value uniform 6000000;'));
await put('0/O2',scalar('O2','[0 0 0 0 0 0 0]',oxygen,inlet(1),inlet(kind==='oxygen'?1:0)));
await put('0/H2',scalar('H2','[0 0 0 0 0 0 0]',oxygen.map(y=>1-y),inlet(0),inlet(kind==='oxygen'?0:1)));
await put('0/rhoTarget',scalar('rhoTarget','[1 -3 0 0 0 0 0]',density,'type zeroGradient;','type zeroGradient;'));
await put('0/U',header('U','volVectorField')+`dimensions [0 1 -1 0 0 0 0]; internalField uniform (10 0 0);
boundaryField {left {type pressureInletOutletVelocity; value uniform (10 0 0);} right {type pressureInletOutletVelocity; value uniform (10 0 0);} sides {type empty;}}\n`);
await put('system/fvSchemes',header('fvSchemes')+solverSchemes().replaceAll('Gauss upwind','Gauss limitedLinear 1').replace('div(phi,U) Gauss limitedLinear 1','div(phi,U) Gauss limitedLinearV 1'));
await put('system/fvSolution',header('fvSolution')+`solvers {"p.*" {solver GAMG;smoother GaussSeidel;tolerance 1e-9;relTol 0;}
"(rho|h|U|Yi).*" {solver smoothSolver;smoother symGaussSeidel;tolerance 1e-10;relTol 0;}}
PIMPLE {nOuterCorrectors 2;nCorrectors 2;nNonOrthogonalCorrectors 0;momentumPredictor yes;transonic no;consistent no;pMin 1000;pMax 1e8;pRef 6000000;}
relaxationFactors {equations {".*" 1;}}\n`);
await put('system/controlDict',header('controlDict')+`application reactingFoamSolveZ;libs ("libcombustionModels.so");
startFrom startTime;startTime 0;stopAt endTime;endTime .02;deltaT 1e-7;
adjustTimeStep yes;maxCo .3;maxDeltaT .000005;writeControl adjustableRunTime;writeInterval .005;purgeWrite 0;
writeFormat ascii;writePrecision 14;timeFormat general;timePrecision 14;runTimeModifiable no;writeEnergyBudget yes;fgmThermoCorrectionPasses 3;writeFgmThermoClosure yes;fgmThermoClosureRelativeLimit 1e-8;fgmThermoCorrectionPasses 3;writeFgmThermoClosure yes;fgmThermoClosureRelativeLimit 1e-8;
functions {profiles {type sets;libs ("libsampling.so");writeControl runTime;writeInterval .001;
setFormat csv;interpolationScheme cell;fields (T rho p U O2 H2);
sets (axis {type uniform;axis x;start (-1.995 .005 .005);end (1.995 .005 .005);nPoints 400;});}}\n`);
await put('contact-input.json',JSON.stringify({...plan,erfApproximationMaximumAbsoluteError:1.5e-7},null,2)+'\n');
console.log(JSON.stringify({out,...plan}));
