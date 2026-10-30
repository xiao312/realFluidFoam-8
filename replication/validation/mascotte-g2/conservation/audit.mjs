import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { auditConservation, parseSolverLog, parseFlux } from './core.mjs';
const [manifestPath, option, output] = process.argv.slice(2);
if (!manifestPath || (option && (option !== '--out' || !output)) || process.argv.length > 5) throw new Error('Use audit.mjs INPUT.json [--out NEW_DIR]');
const manifestRaw = await readFile(manifestPath), m = JSON.parse(manifestRaw);
const base = dirname(resolve(manifestPath)), hashes = [];
const hash = raw => createHash('sha256').update(raw).digest('hex');
async function input(spec, role) {
  if (!spec?.path || !/^[a-f0-9]{64}$/.test(spec.sha256 ?? '')) throw new Error(`Missing frozen input: ${role}`);
  const path = resolve(base, spec.path), raw = await readFile(path);
  if (hash(raw) !== spec.sha256) throw new Error(`Hash mismatch: ${role}`);
  hashes.push({ role, path, sha256: spec.sha256, bytes: raw.length });
  return raw.toString();
}
if (m.schema !== 'g2-discrete-conservation-input-v1' || m.staticMesh !== true || m.energyForm !== 'absoluteEnthalpy' ||
    !/^[a-f0-9]{40}$/.test(m.solverSourceCommit ?? '') || !/^[a-f0-9]{64}$/.test(m.solverExecutableSha256 ?? '')) throw new Error('Unsupported formulation or missing source/executable identity');
const files = {};
for (const name of ['EEqn.H', 'energyState.H', 'pEqn.H', 'reactingFoamSolveZ.C']) files[name] = await input(m.sourceFiles?.[name], `source:${name}`);
const strip = text => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
const compact = text => strip(text).replace(/\s+/g, '');
const equation = compact(files['EEqn.H']), state = compact(files['energyState.H']);
const pressure = compact(files['pEqn.H']), main = compact(files['reactingFoamSolveZ.C']);
const sourceConventions = {
  conservativeEnthalpyDdt: equation.includes('energyDdt(fvm::ddt(rho,he))'),
  explicitKineticTerm: equation.includes('fvc::ddt(rho,K)+fvc::div(phi,K)'),
  enthalpyPressureWork: equation.includes(':-dpdt'),
  finalStateDefinition: state.includes('<<"E="<<H+KE-(thermo.he().name()=="h"?PV:0)'),
  conservativeStateIntegrals: state.includes('fvc::domainIntegrate(rho*transportedEnergy)') && state.includes('fvc::domainIntegrate(rho*K)'),
  pressureRefresh: pressure.includes('dpdt=fvc::ddt(p)') && pressure.includes('K=0.5*magSqr(U)'),
  energyBeforePressure: main.includes('#include"EEqn.H"') && main.includes('#include"pEqn.H"') &&
    main.indexOf('#include"EEqn.H"') < main.indexOf('#include"pEqn.H"'),
  finalStateAfterEosRho: main.includes('rho=thermo.rho();') && main.includes('#include"energyState.H"') &&
    main.lastIndexOf('rho=thermo.rho();') < main.lastIndexOf('#include"energyState.H"'),
  noMeshMotionCall: !main.includes('mesh.update('),
};
if (!Object.values(sourceConventions).every(Boolean)) throw new Error(`Unsupported source conventions: ${JSON.stringify(sourceConventions)}`);
const control = strip(await input(m.caseFiles?.controlDict, 'case:controlDict'));
const schemes = strip(await input(m.caseFiles?.fvSchemes, 'case:fvSchemes'));
if (!/fgmEnergyForm\s+absoluteEnthalpy\s*;/.test(control)) throw new Error('Executing case does not select absolute enthalpy');
const ddt = /ddtSchemes\s*\{([^{}]*)\}/.exec(schemes)?.[1];
const entries = ddt?.split(';').map(s => s.trim()).filter(Boolean);
if (!entries?.length || !entries.every(s => /\sEuler$/.test(s)) || !entries.some(s => /^default\s+Euler$/.test(s))) throw new Error('Explicit Euler ddt schemes required');
if (m.executionReceipt) await input(m.executionReceipt, 'execution-receipt');
const log = await input(m.log, 'solver-log'), flux = {};
for (const [patch, sources] of Object.entries(m.massFluxFiles ?? {})) {
  if (!Array.isArray(sources)) throw new Error(`Expected file list for ${patch}`);
  flux[patch] = [];
  for (const file of sources) flux[patch].push(...parseFlux(await input(file, `phi:${patch}`), file.path));
}
const report = auditConservation(parseSolverLog(log), flux, m.boundaryCoverage);
const here = dirname(fileURLToPath(import.meta.url));
Object.assign(report, { jobId: m.jobId, solverSourceCommit: m.solverSourceCommit,
  solverExecutableSha256: m.solverExecutableSha256, sourceConventions,
  inputManifestSha256: hash(manifestRaw), inputs: hashes,
  auditor: { 'audit.mjs': hash(await readFile(`${here}/audit.mjs`)), 'core.mjs': hash(await readFile(`${here}/core.mjs`)) },
  terminatedNormally: /\nEnd\s*(?:\n|$)/.test(log) && !/FOAM FATAL|Floating point exception/.test(log),
  unloggedMassSources: m.unloggedMassSources ?? 'not independently accounted',
  unloggedEnergySources: m.unloggedEnergySources ?? 'not independently accounted',
  executionBindingQualification: m.executionReceipt ? 'Supplied immutable receipt retained; executable/source relationship requires review of that receipt' : 'No execution receipt supplied',
});
if (option === '--out') {
  const out = resolve(output); await mkdir(out);
  await writeFile(`${out}/report.json`, JSON.stringify(report, null, 2) + '\n');
  const columns = ['index', 'previousTime_s', 'time_s', 'dt_s', 'energyStatus', 'massStatus', 'timeName',
    'finalStateEnergyDefect_J', 'enthalpyCouplingDifference_J', 'pressureCouplingDifference_J', 'assembledTermDefect_J',
    'loggedEquationResidual_W', 'loggedEquationResidualL1_W', 'equationTermMinusResidual_W', 'kineticBoundaryPowerEstimate_W',
    'energyThroughputScale_J', 'sensibleInventoryScale_J', 'defectPerThroughput', 'defectPerSensibleInventory',
    'cumulativeEnergyDefect_J', 'netOutwardMassFlow_kg_s', 'eulerBoundaryMass_kg', 'finalStateMassDefect_kg', 'massThroughputScale_kg',
    'massDefectPerThroughput', 'cumulativeMassDefect_kg', 'cumulativeEulerBoundaryMass_kg'];
  const csv = [columns.join(','), ...report.steps.map(row => columns.map(key => row[key] ?? '').join(','))].join('\n') + '\n';
  await writeFile(`${out}/steps.csv`, csv);
  console.log(JSON.stringify({ output: out, status: report.status, statistics: report.statistics,
    completedThroughTime_s: report.completedThroughTime_s, scientificAcceptance: false }, null, 2));
} else console.log(JSON.stringify(report, null, 2));
