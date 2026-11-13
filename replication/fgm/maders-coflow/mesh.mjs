import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

// Geometry algorithm reused from our existing G2 wedge generator.
// This is a structured reconstruction, not the author's unavailable mesh.
const options = Object.fromEntries(process.argv.slice(2).reduce((pairs, key, i, all) => {
  if (key.startsWith('--')) pairs.push([key.slice(2), all[i + 1]?.startsWith('--') ? true : all[i + 1] ?? true]);
  return pairs;
}, []));
const here = path.dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(fs.readFileSync(path.join(here, 'case.json'), 'utf8').replace(/^\uFEFF/, ''));
const protocol=options.protocol??'baseline';
if(!['baseline','paper','paper-fine'].includes(protocol))throw Error('Unknown mesh protocol');
const paper=protocol!=='baseline';
const axialCells=Number(options['axial-cells']??(paper?(protocol==='paper-fine'?1667:500):250));
if(!Number.isInteger(axialCells)||axialCells<1)throw Error('Axial cells must be a positive integer');
const recipe = { axialLength_m: config.height_m, radialBounds_m: paper?[0,.003,config.fuel_radius_m,.012,config.outer_radius_m]:[0,config.fuel_radius_m,config.outer_radius_m],
  axialCells, radialCells: paper?[30,50,100,60]:[60,100], halfAngle_deg: 2.5, azimuthalCells: 1,
  source: 'Verhoeven2011 PDF p44; Maders2017 geometry radius labels corrected',
  protocol, axialSpacing_m: config.height_m/axialCells, limitation: 'Structured reconstruction; author unstructured mesh unavailable; zero-thickness inlet lip. Paper120k uses60um radial front/200um axial; paper-fine uses60um axial.' };
if (!options.out || options.plan) {
  console.log(JSON.stringify({ mode: 'plan', recipe, output: options.out ?? null }, null, 2));
} else {
  const output = path.resolve(options.out);
  if (fs.existsSync(output)) throw Error('Refusing existing case directory');
  const vertices = [], indices = new Map(), blocks = [];
  const angle = recipe.halfAngle_deg * Math.PI / 180;
  function vertex(end, radial, side) {
    const r = recipe.radialBounds_m[radial];
    const key = `${end}/${radial}/${r === 0 ? 0 : side}`;
    if (!indices.has(key)) {
      indices.set(key, vertices.length);
      vertices.push([end * recipe.axialLength_m, r * Math.cos(angle), side * r * Math.sin(angle)]);
    }
    return indices.get(key);
  }
  for (let band = 0; band < recipe.radialCells.length; band++) blocks.push({ vertices: [vertex(0, band, -1), vertex(1, band, -1),
    vertex(1, band + 1, -1), vertex(0, band + 1, -1), vertex(0, band, 1), vertex(1, band, 1),
    vertex(1, band + 1, 1), vertex(0, band + 1, 1)], cells: [recipe.axialCells, recipe.radialCells[band], 1] });
  const patches = { fuel: [], air: [], outlet: [], outerWall: [], axis: [], planeMinus: [], planePlus: [] };
  blocks.forEach(({ vertices: v }, band) => {
    patches[recipe.radialBounds_m[band+1]<=config.fuel_radius_m ? 'fuel' : 'air'].push([v[0], v[4], v[7], v[3]]);
    patches.outlet.push([v[1], v[2], v[6], v[5]]);
    patches.planeMinus.push([v[0], v[3], v[2], v[1]]);
    patches.planePlus.push([v[4], v[5], v[6], v[7]]);
    if (band === 0) patches.axis.push([v[0], v[1], v[5], v[4]]);
    else if(band===recipe.radialCells.length-1) patches.outerWall.push([v[3], v[7], v[6], v[2]]);
  });
  const tuple = x => `(${x.join(' ')})`;
  const header = name => `FoamFile { version 2.0; format ascii; class dictionary; object ${name}; }\n`;
  const types = { fuel: 'patch', air: 'patch', outlet: 'patch', outerWall: 'wall', axis: 'empty', planeMinus: 'wedge', planePlus: 'wedge' };
  const dictionary = header('blockMeshDict') + 'convertToMeters 1;\nvertices\n(\n' + vertices.map(tuple).join('\n') +
    '\n);\nblocks\n(\n' + blocks.map(b => `hex ${tuple(b.vertices)} ${tuple(b.cells)} simpleGrading (1 1 1)`).join('\n') +
    '\n);\nedges ();\nboundary\n(\n' + Object.entries(patches).map(([name, faces]) =>
      `${name} { type ${types[name]}; faces (${faces.map(tuple).join(' ')}); }`).join('\n') + '\n);\nmergePatchPairs ();\n';
  fs.mkdirSync(path.join(output, 'system'), { recursive: true });
  fs.mkdirSync(path.join(output, 'constant'));
  fs.mkdirSync(path.join(output, '0'));
  fs.writeFileSync(path.join(output, 'system/blockMeshDict'), dictionary);
  fs.writeFileSync(path.join(output, 'system/controlDict'), header('controlDict') + 'application blockMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 0.001; writeControl timeStep; writeInterval 1;\n');
  fs.writeFileSync(path.join(output, 'system/fvSchemes'), header('fvSchemes') + 'ddtSchemes { default Euler; } gradSchemes { default Gauss linear; } divSchemes { default none; } laplacianSchemes { default Gauss linear corrected; } interpolationSchemes { default linear; } snGradSchemes { default corrected; }\n');
  fs.writeFileSync(path.join(output, 'system/fvSolution'), header('fvSolution') + 'solvers {}\n');
  fs.writeFileSync(path.join(output, 'mesh-input.json'), JSON.stringify({ recipe,
    blockMeshDict_sha256: createHash('sha256').update(dictionary).digest('hex'),
    expected_cells: recipe.axialCells * recipe.radialCells.reduce((a,b) => a+b, 0),
    meshed: false, CFD_executed: false }, null, 2) + '\n');
  console.log(JSON.stringify({ output, recipe, expected_cells: recipe.axialCells*recipe.radialCells.reduce((a,b)=>a+b,0) }));
}
