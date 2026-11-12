import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { solverSchemes } from '../../validation/fgm-of8/direct-verification/schemes.mjs';

const options = {};
for (let i=2; i<process.argv.length; i++) {
  const key=process.argv[i];
  if (key === '--plan') options.plan=true;
  else if (['--table','--out','--end-time','--ranks'].includes(key) && process.argv[i+1]) options[key.slice(2)]=process.argv[++i];
  else throw Error(`Unknown or missing option ${key}`);
}
if (!options.table) throw Error('Use --table TABLE_DIRECTORY [--out NEW_CASE] [--plan]');
const here=path.dirname(fileURLToPath(import.meta.url));
const table=path.resolve(options.table);
const receipt=JSON.parse(fs.readFileSync(path.join(table,'receipt.json')));
const metadata=JSON.parse(fs.readFileSync(path.join(table,'phase-metadata.json')));
const init=JSON.parse(fs.readFileSync(path.join(table,'initialization.json')));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const tableBytes=fs.readFileSync(path.join(table,'physical.tbl'));
if (hash(tableBytes)!==receipt.table_sha256) throw Error('Physical table digest differs');
if (hash(fs.readFileSync(path.join(table,'phase-metadata.json')))!==receipt.metadata_sha256) throw Error('Thermo metadata digest differs');
const endTime=Number(options['end-time']??.05),ranks=Number(options.ranks??8);
if (!Number.isFinite(endTime)||endTime<=0||endTime>2||!Number.isInteger(ranks)||ranks<1||ranks>32) throw Error('Invalid duration/ranks');
const plan={target:'maders2017-fig-4',table_sha256:receipt.table_sha256,source_commit:receipt.source_commit,
  clean_start_time_s:0,end_time_s:endTime,ranks,
  models:{thermo:'NASA7/perfectGas',transport:'Smooke Cp-dependent mu/kappa; stock OF8 Fourier unity-Le diffusion',
    combustion:'FGM weighted raw progress; absolute-Ha energy; signed source integration',
    buoyancy:'stock fvOptions buoyancyForce(U) and buoyancyEnergy(Ha), g=(-9.81,0,0)'},
  limits:['Structured40000-cell reconstructed mesh; author mesh unavailable','First diagnostic uses upwind convection; paper reports second order',
    'Fresh hot ring at timezero; differs from paper cold-steady-first numerical initialization',
    '0.05s is a startup diagnostic, not assumed steady or paper accepted']};
if (options.plan||!options.out) {console.log(JSON.stringify(plan,null,2));process.exit(0);}
const out=path.resolve(options.out);
if(fs.existsSync(out))throw Error('Refusing existing case; all CFD starts clean');
const mesh=spawnSync(process.execPath,[path.join(here,'mesh.mjs'),'--out',out],{encoding:'utf8'});
if(mesh.status!==0)throw Error(mesh.stderr||mesh.stdout||'Mesh case generation failed');
const header=(name,cls='dictionary')=>`FoamFile { version 2.0; format ascii; class ${cls}; object "${name}"; }\n`;
const put=(file,text)=>fs.writeFileSync(path.join(out,file),text);
const names=metadata.species.map(s=>s.name);
const thermo=spawnSync(process.execPath,[path.resolve(here,'../../validation/fgm-of8/direct-verification/thermo-export.mjs'),
  path.join(table,'phase-metadata.json'),'--out',path.join(out,'thermo-input'),'--nasa-extrapolation','290,3500'],{encoding:'utf8'});
if(thermo.status!==0)throw Error(thermo.stderr||thermo.stdout||'NASA export failed');
const thermoText=fs.readFileSync(path.join(out,'thermo-input/thermophysicalProperties'),'utf8')
  .replace('transport const;','transport smooke;');
put('constant/thermophysicalProperties',thermoText);
fs.copyFileSync(path.join(table,'physical.tbl'),path.join(out,'constant/physical.tbl'));
const scalarBoundary=(fuel,air)=>`boundaryField {
 fuel { type fixedValue; value uniform ${fuel}; }
 air { type fixedValue; value uniform ${air}; }
 outlet { type zeroGradient; } outerWall { type zeroGradient; }
 axis { type empty; } planeMinus { type wedge; } planePlus { type wedge; }
}\n`;
function scalar(name,dimensions,value,fuel,air){
  put(`0/${name}`,header(name,'volScalarField')+`dimensions [${dimensions}];\ninternalField uniform ${value};\n`+scalarBoundary(fuel,air));
}
for(let i=0;i<names.length;i++)scalar(names[i],'0 0 0 0 0 0 0',init.cold_air_Y[i],init.cold_fuel_Y[i],init.cold_air_Y[i]);
scalar('Z','0 0 0 0 0 0 0',0,1,0);
scalar('c','0 0 0 0 0 0 0',0,0,0);
scalar('T','0 0 0 1 0 0 0',298,298,298);
scalar('Ha','0 2 -2 0 0 0 0',init.cold_air_Ha_J_kg,init.cold_fuel_Ha_J_kg,init.cold_air_Ha_J_kg);
put('0/p',header('p','volScalarField')+`dimensions [1 -1 -2 0 0 0 0]; internalField uniform 101325;
boundaryField { fuel { type zeroGradient; } air { type zeroGradient; }
 outlet { type fixedValue; value uniform 101325; } outerWall { type zeroGradient; }
 axis { type empty; } planeMinus { type wedge; } planePlus { type wedge; } }\n`);
put('0/U',header('U','volVectorField')+`dimensions [0 1 -1 0 0 0 0]; internalField uniform (0.23 0 0);
boundaryField {
 fuel { type fixedValue; value uniform (0.115 0 0); }
 air { type fixedValue; value uniform (0.23 0 0); }
 outlet { type pressureInletOutletVelocity; value uniform (0 0 0); }
 outerWall { type noSlip; } axis { type empty; } planeMinus { type wedge; } planePlus { type wedge; }
}\n`);
put('constant/g',header('g','uniformDimensionedVectorField')+'dimensions [0 1 -2 0 0 0 0]; value (-9.81 0 0);\n');
put('constant/fvOptions',header('fvOptions')+`gravityForce { type buoyancyForce; active yes; buoyancyForceCoeffs { fields (U); } }
gravityEnergy { type buoyancyEnergy; active yes; buoyancyEnergyCoeffs { fields (Ha); U U; } }\n`);
put('constant/momentumTransport',header('momentumTransport')+'simulationType laminar;\n');
put('constant/thermophysicalTransport',header('thermophysicalTransport')+'laminar { model Fourier; }\n');
put('constant/combustionProperties',header('combustionProperties')+`combustionModel fgmTable;
fgmTableCoeffs { table "${path.join(out,'constant/physical.tbl').replaceAll('\\','/')}"; boundsPolicy error; mixtureFractionField Z; progressField c; speciesSumLimit 1e-8; }\n`);
put('system/fvSchemes',header('fvSchemes')+solverSchemes());
put('system/fvSolution',header('fvSolution')+`solvers {
 "p.*" { solver GAMG; smoother GaussSeidel; tolerance 1e-9; relTol 0; }
 "rho.*" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-11; relTol 0; }
 "(U|h|Ha|Z|c|Yi).*" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-11; relTol 0; }
}
PIMPLE { pMin 90000; pMax 120000; pRef 101325; momentumPredictor yes; transonic no; consistent no;
 nOuterCorrectors 2; nCorrectors 2; nNonOrthogonalCorrectors 0; }
relaxationFactors { equations { ".*" 1; } }\n`);
put('system/decomposeParDict',header('decomposeParDict')+`numberOfSubdomains ${ranks}; method simple; simpleCoeffs { n (${ranks} 1 1); delta 0.001; }\n`);
const writeInterval=endTime/10;
const sample=`radialProfiles { type sets; libs ("libsampling.so"); writeControl runTime; writeInterval ${writeInterval};
 interpolationScheme cellPoint; setFormat csv; fields (T CO CO2 Z c U rho);
 sets ( h10 { type lineUniform; axis y; start (0.01 0.000001 0); end (0.01 0.02749 0); nPoints 250; }
 h40 { type lineUniform; axis y; start (0.04 0.000001 0); end (0.04 0.02749 0); nPoints 250; } ); }`;
const flux=['fuel','air','outlet'].map(p=>`massFlux_${p} { type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl runTime; writeInterval ${writeInterval}; regionType patch; name ${p}; operation sum; fields (phi); writeFields no; log no; }`).join('\n');
put('system/controlDict',header('controlDict')+`application reactingFoamSolveZ;
libs ("libcombustionModels.so" "libmadersThermo.so"); startFrom startTime; startTime 0;
stopAt endTime; endTime ${endTime}; deltaT 1e-7; adjustTimeStep yes; maxCo 0.5; maxDeltaT 0.0001;
writeControl adjustableRunTime; writeInterval ${writeInterval}; purgeWrite 0; writeFormat ascii;
writePrecision 14; timeFormat general; timePrecision 12; runTimeModifiable no;
fgmEnergyForm absoluteEnthalpy; fgmRequireHaInitialization yes; writeEnergyBudget yes;
writeFgmThermoClosure yes; fgmThermoClosureRelativeLimit 1e-8; fgmProgressSourceEnabled yes;
fgmSourceIntegration strangFixedState; fgmSkipUnusedDimix no;
conserveTabulatedDensity yes; projectTabulatedZRoundoff yes; writeMixtureFractionBudget yes;
functions { ${sample}\n${flux} }\n`);
const hotValues=[`volScalarFieldValue Z ${init.Z}`,`volScalarFieldValue c ${init.C}`,
  `volScalarFieldValue T ${init.T_K}`,`volScalarFieldValue Ha ${init.Ha_J_kg}`,
  ...names.map((n,i)=>`volScalarFieldValue "${n}" ${init.Y[i]}`)].join('\n');
put('system/setFieldsDict',header('setFieldsDict')+`defaultFieldValues ();
regions ( cylinderToCell { p1 (0 0 0); p2 (0.1 0 0); radius 0.006;
 fieldValues (volScalarFieldValue Z 1 volScalarFieldValue c 0 volScalarFieldValue T 298
 volScalarFieldValue Ha ${init.cold_fuel_Ha_J_kg}
 ${names.map((n,i)=>`volScalarFieldValue "${n}" ${init.cold_fuel_Y[i]}`).join('\n')}); }
 cylinderToCell { p1 (0 0 0); p2 (0.004 0 0); radius 0.007;
 fieldValues (${hotValues}); }
 cylinderToCell { p1 (0 0 0); p2 (0.004 0 0); radius 0.005;
 fieldValues (volScalarFieldValue Z 1 volScalarFieldValue c 0 volScalarFieldValue T 298
 volScalarFieldValue Ha ${init.cold_fuel_Ha_J_kg}
 ${names.map((n,i)=>`volScalarFieldValue "${n}" ${init.cold_fuel_Y[i]}`).join('\n')}); } );\n`);
put('maders-case-input.json',JSON.stringify({...plan,initialization:init,physical_table_receipt:receipt},null,2)+'\n');
console.log(JSON.stringify({created:out,...plan},null,2));
