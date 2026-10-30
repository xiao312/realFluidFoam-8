import { mkdir, writeFile, copyFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { loadPhysicalTable, thermoState } from '../../fgm-of8/direct-verification/physical-input.mjs';
import { inspectMesh, copyMesh } from './mesh-input.mjs';

const options = {}, args = process.argv.slice(2);
for (let i = 0; i < args.length; i += 2) {
  if (!['--table-dir', '--metadata', '--mesh-dir', '--out', '--bounds', '--end-time', '--ranks'].includes(args[i]) || !args[i + 1]) {
    throw new Error('Use --table-dir DIR --metadata FILE --mesh-dir DIR [--out NEW_CASE] [--bounds error|clamp] [--end-time S] [--ranks N]');
  }
  options[args[i].slice(2)] = args[i + 1];
}
for (const key of ['table-dir', 'metadata', 'mesh-dir']) if (!options[key]) throw new Error(`Missing --${key}`);
const bounds = options.bounds ?? 'error', endTime = Number(options['end-time'] ?? 2e-5);
const ranks = Number(options.ranks ?? 2);
if (!['error', 'clamp'].includes(bounds) || !(endTime > 0 && endTime <= 0.1) ||
    !Number.isInteger(ranks) || ranks < 1 || ranks > 64) throw new Error('Invalid diagnostic bounds, duration or ranks');
const input = await loadPhysicalTable(resolve(options['table-dir']), resolve(options.metadata));
const mesh = await inspectMesh(resolve(options['mesh-dir']));
const pressure = input.receipt.case.pressure_pa;
if (!(pressure > 0 && Number.isFinite(pressure))) throw new Error('Missing physical table pressure');
const names = input.metadata.species.map(s => s.name);
const streams = { ch4inlet: input.lookup(1, 0), loxinlet: input.lookup(0, 0) };
const initial = input.lookup(0.2, 0.5);
for (const state of [...Object.values(streams), initial]) {
  if (!(state.temperature >= 200 && state.temperature <= 6000)) throw new Error('Warm diagnostic requires 200..6000 K input states');
  state.thermo = thermoState(input.metadata, state.y, state.temperature);
  state.density = pressure / (state.thermo.gasConstant * state.temperature);
  if (!(state.density > 0 && state.thermo.cv > 0)) throw new Error('Invalid thermodynamic state');
}
const flows = { ch4inlet: 0.1431, loxinlet: 0.0444 };
for (const [patch, state] of Object.entries(streams)) {
  state.fullAnnulusMassFlow_kg_s = flows[patch];
  state.massFlow_kg_s = flows[patch] * mesh.patches[patch].wedgeAreaFraction;
  state.meanVelocity_m_s = state.massFlow_kg_s / (state.density * mesh.patches[patch].area);
}
const slowerInlet = Math.min(...Object.values(streams).map(s => s.meanVelocity_m_s));
const plan = { schema: 'forge-direct-warm-g2-fgm-v1', startTime: 0, endTime, pressure, ranks,
  energyForm: 'absoluteEnthalpy', boundsPolicy: bounds, initial, streams, mesh,
  inputHashes: input.inputHashes, sourceTableCase: input.receipt.case,
  approximations: ['warm ideal-gas thermo', 'constant viscosity and Prandtl number', 'unity Lewis diffusion',
    'laminar resolved diagnostic', 'retained wedge geometry differs from paper',
    'uniform partly reacted initial fill', 'early transient, not steady morphology'],
  convectiveTimes_s: { axial50mm: 0.05 / slowerInlet, chamber200mm: 0.2 / slowerInlet,
    interpretation: 'Inlet-based scale only; recirculation and flame relaxation may be slower.' },
  paperReplicationQualified: false, scientificAcceptance: false };
if (!options.out) { console.log(JSON.stringify({ dryRun: true, ...plan }, null, 2)); process.exit(0); }
const out = resolve(options.out), here = dirname(fileURLToPath(import.meta.url));
await mkdir(out); // A new directory is mandatory: no evolved CFD is imported.
for (const dir of ['0', 'constant', 'system']) await mkdir(`${out}/${dir}`);
const header = (object, cls = 'dictionary') => `FoamFile { version 2.0; format ascii; class ${cls}; object "${object}"; }\n`;
const put = (path, data) => writeFile(`${out}/${path}`, data);
const result = spawnSync(process.execPath, [resolve(here, '../../fgm-of8/direct-verification/thermo-export.mjs'),
  resolve(options.metadata), '--out', `${out}/thermo-input`], { encoding: 'utf8' });
if (result.status !== 0) throw new Error(result.stderr || result.stdout || 'Thermo export failed');
await copyFile(`${out}/thermo-input/thermophysicalProperties`, `${out}/constant/thermophysicalProperties`);
await copyMesh(resolve(options['mesh-dir']), out);
await put('constant/physical.tbl', input.raw);
const scalarBoundary = (fuel, oxygen, initialValue) => `boundaryField {
 geom { type zeroGradient; } slipwalls { type zeroGradient; } noslipwalls { type zeroGradient; }
 ch4inlet { type fixedValue; value uniform ${fuel}; }
 loxinlet { type fixedValue; value uniform ${oxygen}; }
 axisymmetric { type symmetry; }
 outlet { type inletOutlet; inletValue uniform ${initialValue}; value uniform ${initialValue}; }
 planeMinus { type wedge; } planePlus { type wedge; }
}\n`;
async function scalar(name, dimensions, value, inletValue) {
  await put(`0/${name}`, header(name, 'volScalarField') + `dimensions [${dimensions}];
internalField uniform ${value};\n` + scalarBoundary(inletValue(streams.ch4inlet), inletValue(streams.loxinlet), value));
}
for (let i = 0; i < names.length; i++) await scalar(names[i], '0 0 0 0 0 0 0', initial.y[i], s => s.y[i]);
await scalar('Z', '0 0 0 0 0 0 0', initial.z, s => s.z);
await scalar('c', '0 0 0 0 0 0 0', initial.c, s => s.c);
await scalar('T', '0 0 0 1 0 0 0', initial.temperature, s => s.temperature);
await scalar('Ha', '0 2 -2 0 0 0 0', initial.thermo.enthalpy, s => s.thermo.enthalpy);
await put('0/p', header('p', 'volScalarField') + `dimensions [1 -1 -2 0 0 0 0];
internalField uniform ${pressure};
boundaryField {
 geom { type zeroGradient; } slipwalls { type zeroGradient; } noslipwalls { type zeroGradient; }
 ch4inlet { type zeroGradient; } loxinlet { type zeroGradient; } axisymmetric { type symmetry; }
 outlet { type fixedValue; value uniform ${pressure}; }
 planeMinus { type wedge; } planePlus { type wedge; }
}\n`);
const velocityInlet = name => `${name} { type flowRateInletVelocity;
 massFlowRate ${streams[name].massFlow_kg_s}; rho rho; rhoInlet ${streams[name].density};
 value uniform (${streams[name].meanVelocity_m_s} 0 0); }`;
await put('0/U', header('U', 'volVectorField') + `dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField { geom { type noSlip; } slipwalls { type slip; } noslipwalls { type noSlip; }
 ${velocityInlet('ch4inlet')} ${velocityInlet('loxinlet')}
 axisymmetric { type symmetry; } outlet { type pressureInletOutletVelocity; value uniform (0 0 0); }
 planeMinus { type wedge; } planePlus { type wedge; }
}\n`);
await put('constant/momentumTransport', header('momentumTransport') + 'simulationType laminar;\n');
await put('constant/combustionProperties', header('combustionProperties') + `combustionModel fgmTable;
fgmTableCoeffs { table "physical.tbl"; boundsPolicy ${bounds}; mixtureFractionField Z;
 progressField c; speciesSumLimit 1e-8; }\n`);
await put('system/fvSchemes', header('fvSchemes') + `ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes { default none; div(phi,U) Gauss upwind; div(phi,Yi_h) Gauss upwind;
 div(phi,Z) Gauss upwind; div(phi,c) Gauss upwind; div(phi,h) Gauss upwind;
 div(phi,Ha) Gauss upwind; div(phi,K) Gauss upwind; div(phiv,p) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
fluxRequired { default no; p; }\n`);
await put('system/fvSolution', header('fvSolution') + `solvers {
 "p.*" { solver GAMG; smoother GaussSeidel; tolerance 1e-9; relTol 0; }
 "(rho|U|h|Ha|Z|c|Yi).*" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-10; relTol 0; }
}
PIMPLE { pMin 1000; pMax 1e8; pRef ${pressure}; momentumPredictor yes;
 nOuterCorrectors 2; nCorrectors 2; nNonOrthogonalCorrectors 0; }
relaxationFactors { equations { ".*" 1; } }\n`);
await put('system/decomposeParDict', header('decomposeParDict') + `numberOfSubdomains ${ranks};
method simple; simpleCoeffs { n (${ranks} 1 1); delta 0.001; }\n`);
await put('system/controlDict', header('controlDict') + `application reactingFoamSolveZ;
libs ("libcombustionModels.so"); startFrom startTime; startTime 0;
stopAt endTime; endTime ${endTime}; deltaT ${Math.min(1e-9, endTime / 100)};
adjustTimeStep yes; maxCo 0.4; maxDeltaT ${Math.min(1e-7, endTime / 20)};
writeControl adjustableRunTime; writeInterval ${endTime / 4}; purgeWrite 0;
writeFormat ascii; writePrecision 12; writeCompression off;
timeFormat general; timePrecision 12; runTimeModifiable no;
fgmEnergyForm absoluteEnthalpy; writeEnergyBudget yes;
functions {
 samples { type sets; libs ("libsampling.so"); writeControl writeTime;
  interpolationScheme cellPoint; setFormat raw; fields (T Z c CH4 O2 CO2 CO OH Ha);
  sets (
   nearAxis { type uniform; axis x; start (0.0001 0.0001 0); end (0.1999 0.0001 0); nPoints 400; }
   radial30mm { type uniform; axis y; start (0.03 0.0001 0); end (0.03 0.0248 0); nPoints 200; }
   radial60mm { type uniform; axis y; start (0.06 0.0001 0); end (0.06 0.0248 0); nPoints 200; }
  );
 }
 ${['ch4inlet', 'loxinlet', 'outlet'].map(patch => `massFlux_${patch} {
  type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 10;
  regionType patch; name ${patch}; operation sum; fields (phi); writeFields no; log yes;
 }`).join('\n')}
}\n`);
await put('direct-g2-input.json', JSON.stringify(plan, null, 2) + '\n');
await put('mesh-input-audit.json', JSON.stringify(mesh, null, 2) + '\n');
console.log(JSON.stringify({ created: out, ...plan }, null, 2));
