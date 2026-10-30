import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const args = process.argv.slice(2);
const options = {};
for (let i = 0; i < args.length; i += 2) {
  if (!['--out', '--kind', '--cells', '--delta-t'].includes(args[i]) || !args[i + 1]) {
    throw new Error('Usage: prepare.mjs [--out NEW_DIR] --kind heating|contact|conversion [--cells N] [--delta-t S]');
  }
  options[args[i].slice(2)] = args[i + 1];
}
const kind = options.kind ?? 'heating';
if (!['heating', 'contact', 'conversion'].includes(kind)) throw new Error('Unknown problem kind');
const conversion = kind === 'conversion';
const cells = Number(options.cells ?? (kind === 'contact' ? 80 : 8));
const deltaT = Number(options['delta-t'] ?? (kind === 'contact' ? 1e-4 : 1e-5));
if (!Number.isInteger(cells) || cells < 4 || cells > 10000 || !(deltaT > 0 && deltaT <= 1e-3)) {
  throw new Error('Invalid cells or delta-t');
}
const manifest = {
  schema: 'forge-direct-of8-verification-v1', kind, cells, deltaT,
  length: 0.1, area: 0.0001, startTime: 0,
  endTime: kind === 'contact' ? 0.01 : 0.001,
  velocity: kind === 'contact' ? 1 : 0,
  temperature: 300, pressure: 101325, cp: 1040, molWeight: 28.0134,
  gasConstant: 8314.47, mu: 1.8e-5, pr: 0.72,
  heatRelease: kind === 'contact' ? 0 : 1e6,
  progressSource: kind === 'contact' ? 0 : 0.1,
  energyForm: conversion ? 'absoluteEnthalpy' : 'sensibleEnthalpy',
  chemicalEnergyDrop_J_kg_progress: conversion ? 1e6 : 0,
  tableKind: conversion ? 'analytic-formation-energy-conversion-not-a-flamelet' : 'analytic-constant-composition-not-a-flamelet',
  thresholds: { massRelative: 1e-7, energyRelative: 0.005,
    temperatureIncrementRelative: 0.005, progressIncrementRelative: 1e-5,
    zRmsAbsolute: 0.015, equationResidualRelative: 1e-6 },
};
if (!options.out) {
  console.log(JSON.stringify({ dryRun: true, ...manifest }, null, 2));
  process.exit(0);
}
const out = resolve(options.out);
await mkdir(out); // Refuse existing output: no reuse of evolved CFD states.
for (const dir of ['0', 'constant', 'system']) await mkdir(`${out}/${dir}`);
const header = (object, cls = 'dictionary') =>
  `FoamFile { version 2.0; format ascii; class ${cls}; object ${object}; }\n`;
const put = (name, text) => writeFile(`${out}/${name}`, text);
const cyclic = `boundaryField { left { type cyclic; } right { type cyclic; }
  transverse { type empty; } }\n`;
async function field(name, dimensions, value, vector = false) {
  const internal = Array.isArray(value)
    ? `nonuniform List<scalar>\n${value.length}\n(\n${value.join('\n')}\n)`
    : `uniform ${value}`;
  await put(`0/${name}`, header(name, vector ? 'volVectorField' : 'volScalarField') +
    `dimensions [${dimensions}];\ninternalField ${internal};\n${cyclic}`);
}
await field('U', '0 1 -1 0 0 0 0', `(${manifest.velocity} 0 0)`, true);
await field('p', '1 -1 -2 0 0 0 0', manifest.pressure);
await field('T', '0 0 0 1 0 0 0', manifest.temperature);
for (const [name, value] of [['CH4', conversion ? 0.2 : 0], ['O2', 0], ['N2', conversion ? 0.8 : 1], ['c', 0.2]]) {
  await field(name, '0 0 0 0 0 0 0', value);
}
if (conversion) await field('Ha', '0 2 -2 0 0 0 0', 1040 * (300 - 298.15) - 0.2e6);
const z = kind !== 'contact' ? 0.5 : Array.from({ length: cells }, (_, i) =>
  0.5 + 0.2 * Math.sin(2 * Math.PI * (i + 0.5) / cells));
await field('Z', '0 0 0 0 0 0 0', z);
await put('system/blockMeshDict', header('blockMeshDict') + `
convertToMeters 1;
vertices ((0 0 0) (0.1 0 0) (0.1 0.01 0) (0 0.01 0)
          (0 0 0.01) (0.1 0 0.01) (0.1 0.01 0.01) (0 0.01 0.01));
blocks (hex (0 1 2 3 4 5 6 7) (${cells} 1 1) simpleGrading (1 1 1));
edges ();
boundary (
 left { type cyclic; neighbourPatch right; faces ((0 4 7 3)); }
 right { type cyclic; neighbourPatch left; faces ((1 2 6 5)); }
 transverse { type empty; faces ((0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); }
);
mergePatchPairs ();
`);
await put('system/controlDict', header('controlDict') + `
application reactingFoamSolveZ;
libs ("libcombustionModels.so");
startFrom startTime; startTime 0; stopAt endTime; endTime ${manifest.endTime};
deltaT ${deltaT}; adjustTimeStep no;
writeControl timeStep; writeInterval ${Math.max(1, Math.round(manifest.endTime / deltaT / 10))};
purgeWrite 0; writeFormat ascii; writePrecision 15; writeCompression off;
timeFormat general; timePrecision 12; runTimeModifiable no;
writeEnergyBudget yes;
fgmEnergyForm ${manifest.energyForm};
`);
await put('system/fvSchemes', header('fvSchemes') + `
ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes { default Gauss linear; div(phi,U) Gauss upwind;
 div(phi,Yi_h) Gauss upwind; div(phi,K) Gauss upwind; div(phiv,p) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
fluxRequired { default no; p; }
`);
await put('system/fvSolution', header('fvSolution') + `
solvers {
 "p.*" { solver PCG; preconditioner DIC; tolerance 1e-12; relTol 0; }
 "(rho|U|h|Ha|e|Z|c|Yi|CH4|O2|N2).*" {
  solver smoothSolver; smoother symGaussSeidel; tolerance 1e-12; relTol 0; }
}
PIMPLE { pMin 1000; pMax 1e8; pRef 101325; momentumPredictor yes;
 nOuterCorrectors 4; nCorrectors 2; nNonOrthogonalCorrectors 0; }
relaxationFactors { equations { ".*" 1; } }
`);
await put('constant/momentumTransport', header('momentumTransport') + 'simulationType laminar;\n');
await put('constant/thermophysicalProperties', header('thermophysicalProperties') + `
thermoType { type hePsiThermo; mixture multiComponentMixture; transport const;
 thermo hConst; equationOfState perfectGas; specie specie; energy sensibleEnthalpy; }
inertSpecie N2;
species (CH4 O2 N2);
CH4 { specie { molWeight ${conversion ? 28.0134 : 16.043}; }
 thermodynamics { Cp ${conversion ? 1040 : 2220}; Hf ${conversion ? -1e6 : 0}; }
 transport { mu ${conversion ? 1.8e-5 : 1.1e-5}; Pr 0.72; } }
O2 { specie { molWeight 31.9988; } thermodynamics { Cp 918; Hf 0; }
 transport { mu 2.1e-5; Pr 0.72; } }
N2 { specie { molWeight 28.0134; } thermodynamics { Cp 1040; Hf 0; }
 transport { mu 1.8e-5; Pr 0.72; } }
`);
await put('constant/combustionProperties', header('combustionProperties') + `
combustionModel fgmTable;
fgmTableCoeffs { table "constant.tbl"; boundsPolicy error;
 mixtureFractionField Z; progressField c; speciesSumLimit 1e-8; }
`);
const block = (name, value) => `block ${name}\n${value} ${value}\n${value} ${value}\nend\n`;
await put('constant/constant.tbl', `# Analytic verification only: NOT a chemical flamelet
schema forge-fgm-table-v${conversion ? 2 : 1}
source constant-nitrogen-source-verification
profile-sha256 none
units-progress-source kg/m3/s
units-heat-release W/m3
density-owner thermophysicalModel
temperature-owner thermophysicalModel
enthalpy-owner thermophysicalModel
progress-coordinate ${conversion ? 'mass-fraction-mapped' : 'mass-fraction'}
${conversion ? 'progress-species CH4\nc-min 0 0\nc-max 1 1\n' : ''}
species CH4 O2 N2
nZ 2
nC 2
z 0 1
c 0 1
` + (conversion ? 'block Y CH4\n0 1\n0 1\nend\n' : block('Y CH4', 0)) + block('Y O2', 0) +
  (conversion ? 'block Y N2\n1 0\n1 0\nend\n' : block('Y N2', 1)) +
  block('Sc', manifest.progressSource) + block('Q', manifest.heatRelease) + block('Tdiag', 300));
await put('verification-input.json', JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify({ created: out, ...manifest }, null, 2));
