import { mkdir, writeFile, copyFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { loadPhysicalTable, thermoState } from '../../fgm-of8/direct-verification/physical-input.mjs';
import { inspectMesh, copyMesh } from './mesh-input.mjs';
import { inspectCoarseMesh, copyCoarseMesh } from '../coarse-wedge/mesh.mjs';
import { inspectPaperExitMesh, copyPaperExitMesh } from '../paper-exit-wedge/mesh.mjs';
import { loadRunControls, decompositionDictionary, functionObjects } from './observations.mjs';
import { realFluidInput, initializationInput, ignitionDictionary } from './cold-input.mjs';
import { solverSchemes } from '../../fgm-of8/direct-verification/schemes.mjs';
import { loadSteadyTable, steadyInitialization } from '../steady-flamelet/input.mjs';
import { nasaInversionPolicy } from '../../fgm-of8/direct-verification/thermo-policy.mjs';

const options = {}, args = process.argv.slice(2);
for (let i = 0; i < args.length; i += 2) {
  if (!['--closure', '--table-dir', '--metadata', '--mesh-dir', '--mesh-mode', '--transport-tolerance', '--out', '--bounds', '--end-time', '--ranks', '--observations', '--decomposition', '--thermo-mode', '--thermo-dir', '--initialization', '--chemistry', '--initial-dt', '--max-dt', '--max-co', '--outer', '--nasa-extrapolation', '--source-integration', '--skip-unused-diffusion'].includes(args[i]) || !args[i + 1]) {
    throw new Error('Use --table-dir DIR --metadata FILE --mesh-dir DIR [--mesh-mode registered-200622|coarse-wedge-10000-v1] [--transport-tolerance VALUE] [--out NEW_CASE] [--bounds error|clamp] [--end-time S] [--ranks N] [--observations FILE] [--decomposition FILE] [--thermo-mode warm-ideal|cold-real-fluid --thermo-dir DIR] [--initialization FILE]');
  }
  options[args[i].slice(2)] = args[i + 1];
}
for (const key of ['table-dir', 'metadata', 'mesh-dir']) if (!options[key]) throw new Error(`Missing --${key}`);
const closure = options.closure ?? 'fgm';
if (!['fgm', 'steady-flamelet'].includes(closure)) throw Error('Use --closure fgm|steady-flamelet');
const steady = closure === 'steady-flamelet';
const meshMode = options['mesh-mode'] ?? 'registered-200622';
if (!['registered-200622', 'coarse-wedge-10000-v1', 'paper-exit-wedge-10000-v1'].includes(meshMode)) throw new Error('Use --mesh-mode registered-200622|coarse-wedge-10000-v1|paper-exit-wedge-10000-v1');
const transportTolerance = Number(options['transport-tolerance'] ?? 1e-10);
if (!Number.isFinite(transportTolerance) || transportTolerance < 1e-12 || transportTolerance > 1e-6) {
  throw new Error('--transport-tolerance must be finite and within [1e-12, 1e-6]');
}
const bounds = options.bounds ?? 'error', endTime = Number(options['end-time'] ?? 2e-5);
const ranks = Number(options.ranks ?? 2);
if (!['error', 'clamp'].includes(bounds) || !(endTime > 0 && endTime <= 0.1) ||
    !Number.isInteger(ranks) || ranks < 1 || ranks > 64) throw new Error('Invalid diagnostic bounds, duration or ranks');
const initialDt = Number(options['initial-dt'] ?? Math.min(1e-9, endTime/100));
const maxDt = Number(options['max-dt'] ?? Math.min(1e-7, endTime/20));
const maxCo = Number(options['max-co'] ?? 0.4), outer = Number(options.outer ?? 2);
if (!Number.isFinite(maxCo) || !(maxCo > 0 && maxCo <= 1) || !Number.isInteger(outer) || outer < 1 || outer > 10) {
  throw new Error('Require finite max-co in (0,1] and integer outer in [1,10]');
}
if (![initialDt,maxDt].every(Number.isFinite) || !(initialDt>0 && initialDt<=maxDt && maxDt<=endTime)) throw new Error('Require positive initial-dt <= max-dt <= end-time');
const controls = await loadRunControls(options.observations, options.decomposition, endTime, ranks);
if (steady) controls.observations.instantaneousFields = controls.observations.instantaneousFields.map(name => name === 'fgmTdiag' ? 'steadyTdiag' : name);
const input = await (steady ? loadSteadyTable : loadPhysicalTable)(resolve(options['table-dir']), resolve(options.metadata));
const thermoMode = options['thermo-mode'] ?? 'warm-ideal';
const chemistry = options.chemistry ?? 'table';
if (!['table', 'disabled'].includes(chemistry)) throw new Error('Use --chemistry table|disabled');
const sourceIntegration = options['source-integration'] ?? 'explicit';
if (!['explicit', 'strangFixedState'].includes(sourceIntegration) ||
    (sourceIntegration === 'strangFixedState' && (chemistry !== 'table' || bounds !== 'error'))) {
  throw new Error('strangFixedState requires table chemistry and strict error bounds');
}
const skipUnusedDiffusion = options['skip-unused-diffusion'] ?? 'no';
if (!['yes', 'no'].includes(skipUnusedDiffusion) || (skipUnusedDiffusion === 'yes' && thermoMode !== 'cold-real-fluid')) {
  throw new Error('Unused diffusion suppression requires the qualified full real-fluid runtime');
}
if (!['warm-ideal', 'cold-real-fluid'].includes(thermoMode) || (thermoMode === 'warm-ideal' && options['thermo-dir'])) throw new Error('Explicit valid thermo mode required; a warm case cannot consume a real-fluid directory');
if (steady && (thermoMode !== 'cold-real-fluid' || bounds !== 'error' || chemistry !== 'table' || sourceIntegration !== 'explicit')) throw Error('Steady closure requires cold-real-fluid, strict bounds, table composition and explicit/no split');
const realFluid = thermoMode === 'cold-real-fluid' ? await realFluidInput(options['thermo-dir'], input) : null;
if (realFluid && options['nasa-extrapolation']) throw new Error('Cold input already binds its declared thermodynamic ranges');
const nasaPolicy = realFluid ? null : nasaInversionPolicy(input.metadata, options['nasa-extrapolation']);
const initialization = await (steady ? steadyInitialization : initializationInput)(options.initialization, input);
if (!realFluid && initialization.config.mode === 'localized-covered') throw new Error('Localized preparation currently requires the full-runtime Ha initialization path');
const coarseMesh = meshMode === 'coarse-wedge-10000-v1';
const paperExitMesh = meshMode === 'paper-exit-wedge-10000-v1';
const inspectSelectedMesh = paperExitMesh ? inspectPaperExitMesh : coarseMesh ? inspectCoarseMesh : inspectMesh;
const copySelectedMesh = paperExitMesh ? copyPaperExitMesh : coarseMesh ? copyCoarseMesh : copyMesh;
const mesh = await inspectSelectedMesh(resolve(options['mesh-dir']));
const axisBoundaryType = coarseMesh || paperExitMesh ? 'empty' : 'symmetry';
if (coarseMesh) controls.observations.axialCoordinate = 'x from explicit coarse co-planar inlet at 0 m; separate diagnostic, not registered/paper injector geometry';
if (paperExitMesh) controls.observations.axialCoordinate = 'x from co-planar paper-sized injection exit at 0 m; upstream taper/ducts and square chamber omitted';
const pressure = input.receipt.case.pressure_pa;
if (!(pressure > 0 && Number.isFinite(pressure))) throw new Error('Missing physical table pressure');
const names = input.metadata.species.map(s => s.name);
const streams = { ch4inlet: input.lookup(1, 0), loxinlet: input.lookup(0, 0) };
const initial = initialization.background;
const range = realFluid?.record.effectiveInversionRange_K ?? nasaPolicy.effectiveMixtureIntersection_K;
for (const state of [...Object.values(streams), initial, initialization.hot]) {
  if (!(state.temperature >= range[0] && state.temperature <= range[1])) throw new Error('Input state exceeds declared thermodynamic initialization bounds');
  state.thermo = thermoState(input.metadata, state.y, state.temperature);
  state.density = pressure / (state.thermo.gasConstant * state.temperature);
  if (!(state.density > 0) || (!realFluid && !(state.thermo.cv > 0))) throw new Error('Invalid thermodynamic initialization estimate');
  if (realFluid) state.estimateQualification = 'These NASA/ideal-gas values are placeholders only; executing PR/SRK owns density and Ha.';
}
const flows = { ch4inlet: 0.1431, loxinlet: 0.0444 };
for (const [patch, state] of Object.entries(streams)) {
  state.fullAnnulusMassFlow_kg_s = flows[patch];
  state.massFlow_kg_s = flows[patch] * mesh.patches[patch].wedgeAreaFraction;
  state.meanVelocity_m_s = state.massFlow_kg_s / (state.density * mesh.patches[patch].area);
}
const slowerInlet = Math.min(...Object.values(streams).map(s => s.meanVelocity_m_s));
const plan = { schema: steady ? 'forge-direct-g2-steady-flamelet-v1' : 'forge-direct-warm-g2-fgm-v1', closure,
  ...(steady ? { steadyFlamelet: { fixedChi: input.chi, chiDefinition: input.chiDefinition, transportedProgress: false, addedHeatSource: false,
    originalSteadyConverged: input.receipt.original_steady_numerically_converged, originalResidual: input.receipt.original_final_state_diagnostics,
    temperatureOwner: 'full-SRK thermo inversion of transported Ha', tableTemperature: 'diagnostic and initialization only', pdf: 'laminar delta',
    originalModels: input.receipt.original_models } } : {}), startTime: 0, endTime, pressure, ranks, meshMode,
  timeControls: { initialDt_s: initialDt, maxDt_s: maxDt, maxCo, outerCorrectors: outer },
  linearSolverControls: { transportTolerance, transportFields: steady ? ['U', 'h', 'Ha', 'Z'] : ['U', 'h', 'Ha', 'Z', 'c', 'Yi'],
    pressureTolerance: 1e-9, densityTolerance: 1e-10, relativeTolerance: 0,
    interpretation: 'Linear normalized residual control only; conservation and physical acceptance criteria are unchanged.' },
  energyForm: 'absoluteEnthalpy', chemistry, sourceIntegration,
  skipUnusedDiffusion: skipUnusedDiffusion === 'yes', boundsPolicy: bounds, initial, streams, mesh,
  thermodynamics: realFluid?.record ?? { mode: 'warm-ideal', requiresRuntimeHaInitialization: false, nasaPolicy }, initialization,
  caloricClosure: { required: true, relativeLimit: realFluid ? 1e-8 : 1e-4,
    definition: 'executing sensible h(p,T,Y) versus stored h, scaled by max(1,abs(h),abs(h(p,T,Y)),abs(Cp*T))' },
  ...controls,
  inputHashes: input.inputHashes, sourceTableCase: input.receipt.case,
  approximations: [...(realFluid ? ['PR/SRK with explicitly declared NASA extrapolation', 'fixed-pressure source table without enthalpy coordinate']
    : ['warm ideal-gas thermo', 'constant viscosity and Prandtl number']), 'unity Lewis diffusion',
    'laminar resolved diagnostic', paperExitMesh ? 'paper-sized exit areas on separate coarse wedge; upstream taper/ducts, rim and square chamber omitted' : coarseMesh ? 'separate coarse co-planar wedge; upstream ducts and paper lip omitted' : 'retained wedge geometry differs from paper',
    initialization.interpretation, 'early transient, not steady morphology'],
  convectiveTimes_s: { axial50mm: 0.05 / slowerInlet, chamber200mm: 0.2 / slowerInlet,
    interpretation: realFluid ? 'Ideal-density placeholder estimate only. Use measured ha-initialization-boundaries.csv densities before estimating physical residence times.'
      : 'Inlet-based scale only; recirculation and flame relaxation may be slower.' },
  paperReplicationQualified: false, scientificAcceptance: false };
if (!options.out) { console.log(JSON.stringify({ dryRun: true, ...plan }, null, 2)); process.exit(0); }
const out = resolve(options.out), here = dirname(fileURLToPath(import.meta.url));
await mkdir(out); // A new directory is mandatory: no evolved CFD is imported.
for (const dir of ['0', 'constant', 'system']) await mkdir(`${out}/${dir}`);
const header = (object, cls = 'dictionary') => `FoamFile { version 2.0; format ascii; class ${cls}; object "${object}"; }\n`;
const put = (path, data) => writeFile(`${out}/${path}`, data);
if (realFluid) {
  await mkdir(`${out}/thermo-input`);
  await put('thermo-input/thermophysicalProperties', realFluid.dictionary);
  await put('thermo-input/manifest.json', realFluid.rawManifest);
  await put('constant/thermophysicalProperties', realFluid.dictionary);
} else {
  const result = spawnSync(process.execPath, [resolve(here, '../../fgm-of8/direct-verification/thermo-export.mjs'),
    resolve(options.metadata), '--out', `${out}/thermo-input`,
    ...(options['nasa-extrapolation'] ? ['--nasa-extrapolation', options['nasa-extrapolation']] : [])], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout || 'Thermo export failed');
  await copyFile(`${out}/thermo-input/thermophysicalProperties`, `${out}/constant/thermophysicalProperties`);
}
await copySelectedMesh(resolve(options['mesh-dir']), out);
await put(steady ? 'constant/steady.tbl' : 'constant/physical.tbl', input.raw);
const scalarBoundary = (fuel, oxygen, initialValue) => `boundaryField {
 geom { type zeroGradient; } slipwalls { type zeroGradient; } noslipwalls { type zeroGradient; }
 ch4inlet { type fixedValue; value uniform ${fuel}; }
 loxinlet { type fixedValue; value uniform ${oxygen}; }
 axisymmetric { type ${axisBoundaryType}; }
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
await scalar('Ha', '0 2 -2 0 0 0 0', realFluid ? 0 : initial.thermo.enthalpy, s => realFluid ? 0 : s.thermo.enthalpy);
const ignition = ignitionDictionary(initialization, names);
if (ignition) await put('system/setFieldsDict', ignition);
await put('0/p', header('p', 'volScalarField') + `dimensions [1 -1 -2 0 0 0 0];
internalField uniform ${pressure};
boundaryField {
 geom { type zeroGradient; } slipwalls { type zeroGradient; } noslipwalls { type zeroGradient; }
 ch4inlet { type zeroGradient; } loxinlet { type zeroGradient; } axisymmetric { type ${axisBoundaryType}; }
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
 axisymmetric { type ${axisBoundaryType}; } outlet { type pressureInletOutletVelocity; value uniform (0 0 0); }
 planeMinus { type wedge; } planePlus { type wedge; }
}\n`);
await put('constant/momentumTransport', header('momentumTransport') + 'simulationType laminar;\n');
await put('constant/thermophysicalTransport', header('thermophysicalTransport') + 'laminar { model Fourier; }\n');
await put('constant/combustionProperties', header('combustionProperties') + (steady
  ? `combustionModel steadyFlamelet;
steadyFlameletCoeffs { table "${resolve(out,'constant/steady.tbl').replaceAll('\\','/')}"; fixedChi ${input.chi}; chiDefinition ${input.chiDefinition}; }\n`
  : `combustionModel fgmTable;
fgmTableCoeffs { table "physical.tbl"; boundsPolicy ${bounds}; mixtureFractionField Z;
 progressField c; speciesSumLimit 1e-8; }\n`));
await put('system/fvSchemes', header('fvSchemes') + solverSchemes());
await put('system/fvSolution', header('fvSolution') + `solvers {
 "p.*" { solver GAMG; smoother GaussSeidel; tolerance 1e-9; relTol 0; }
 "rho.*" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-10; relTol 0; }
 "(U|h|Ha|Z|c|Yi).*" { solver smoothSolver; smoother symGaussSeidel; tolerance ${transportTolerance}; relTol 0; }
}
PIMPLE { pMin 1000; pMax 1e8; pRef ${pressure}; momentumPredictor yes;
 transonic no; consistent no;
 nOuterCorrectors ${outer}; nCorrectors 2; nNonOrthogonalCorrectors 0; }
relaxationFactors { equations { ".*" 1; } }\n`);
await put('system/decomposeParDict', header('decomposeParDict') + decompositionDictionary(controls.decomposition, ranks));
await put('system/controlDict', header('controlDict') + `application reactingFoamSolveZ;
libs ("libcombustionModels.so"); startFrom startTime; startTime 0;
stopAt endTime; endTime ${endTime}; deltaT ${initialDt};
adjustTimeStep yes; maxCo ${maxCo}; maxDeltaT ${maxDt};
writeControl adjustableRunTime; writeInterval ${controls.observations.fieldInterval_s}; purgeWrite 0;
writeFormat ascii; writePrecision 12; writeCompression off;
timeFormat general; timePrecision 12; runTimeModifiable no;
fgmEnergyForm absoluteEnthalpy; writeEnergyBudget yes;
writeFgmThermoClosure yes; fgmThermoClosureRelativeLimit ${plan.caloricClosure.relativeLimit};
fgmRequireHaInitialization ${realFluid ? 'yes' : 'no'};
fgmProgressSourceEnabled ${!steady && chemistry === 'table' ? 'yes' : 'no'};
fgmSourceIntegration ${sourceIntegration}; fgmSkipUnusedDimix ${skipUnusedDiffusion};
functions {
 ${functionObjects(controls.observations)}
}\n`);
await put('direct-g2-input.json', JSON.stringify(plan, null, 2) + '\n');
await put('mesh-input-audit.json', JSON.stringify(mesh, null, 2) + '\n');
console.log(JSON.stringify({ created: out, ...plan }, null, 2));
