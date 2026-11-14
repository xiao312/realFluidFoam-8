import { createHash } from 'node:crypto';

export const mode = 'paper-exit-wedge-20000-long-v1';
export const recipe = Object.freeze({ schema: mode, axialLength_m: 0.4,
  halfAngle_deg: 2.5, radialBounds_m: [0, 0.0025, 0.0028, 0.005, 0.025],
  axialCells: 400, radialCells: [8, 6, 10, 26], azimuthalCells: 1,
  grading: [1, 1, 1], upstreamDucts: false, paperGeometryQualified: false,
  coordinateOrigin: 'co-planar injection exit', origin_m: 0, canonicalRawExit_m: 0.01,
  matchedFeatures: ['O2 exit diameter 5 mm', 'lip radial thickness 0.3 mm', 'CH4 annulus diameters 5.6/10 mm'],
  omittedFeatures: ['upstream taper and ducts', 'injector rim/recess', 'square chamber', 'precursor turbulence'] });
export const digest = data => createHash('sha256').update(data).digest('hex');
export const recipeSha256 = digest(JSON.stringify(recipe));
export const patchTypes = { geom: 'wall', slipwalls: 'wall', noslipwalls: 'wall',
  ch4inlet: 'patch', loxinlet: 'patch', axisymmetric: 'empty', outlet: 'patch',
  planeMinus: 'wedge', planePlus: 'wedge' };
export const expectedCounts = { cells: 20000, points: 40501, faces: 80050, internalFaces: 39550 };
export const expectedPatchFaces = { geom: 6, slipwalls: 0, noslipwalls: 426,
  ch4inlet: 10, loxinlet: 8, axisymmetric: 0, outlet: 50,
  planeMinus: 20000, planePlus: 20000 };
export const header = (name, cls = 'dictionary') =>
  `FoamFile { version 2.0; format ascii; class ${cls}; object ${name}; }\n`;

export function geometry() {
  const vertices = [], indices = new Map(), blocks = [];
  const angle = recipe.halfAngle_deg * Math.PI / 180;
  function vertex(xEnd, radial, side) {
    const radius = recipe.radialBounds_m[radial];
    const key = `${xEnd}/${radial}/${radius === 0 ? 0 : side}`;
    if (!indices.has(key)) {
      indices.set(key, vertices.length);
      vertices.push([xEnd * recipe.axialLength_m, radius * Math.cos(angle), side * radius * Math.sin(angle)]);
    }
    return indices.get(key);
  }
  for (let band = 0; band < 4; band++) {
    blocks.push({ vertices: [vertex(0, band, -1), vertex(1, band, -1),
      vertex(1, band + 1, -1), vertex(0, band + 1, -1), vertex(0, band, 1),
      vertex(1, band, 1), vertex(1, band + 1, 1), vertex(0, band + 1, 1)],
    cells: [recipe.axialCells, recipe.radialCells[band], 1] });
  }
  const patches = Object.fromEntries(Object.keys(patchTypes).map(name => [name, []]));
  blocks.forEach(({ vertices: v }, band) => {
    patches[['loxinlet', 'geom', 'ch4inlet', 'noslipwalls'][band]].push([v[0], v[4], v[7], v[3]]);
    patches.outlet.push([v[1], v[2], v[6], v[5]]);
    patches.planeMinus.push([v[0], v[3], v[2], v[1]]);
    patches.planePlus.push([v[4], v[5], v[6], v[7]]);
    if (band === 0) patches.axisymmetric.push([v[0], v[1], v[5], v[4]]);
    if (band === 3) patches.noslipwalls.push([v[3], v[7], v[6], v[2]]);
  });
  return { vertices, blocks, patches };
}

export function blockMeshDictionary() {
  const g = geometry(), tuple = x => `(${x.join(' ')})`;
  return header('blockMeshDict') + `convertToMeters 1;\nvertices\n(\n` +
    g.vertices.map(v => ` ${tuple(v)}`).join('\n') + '\n);\nblocks\n(\n' +
    g.blocks.map(b => ` hex ${tuple(b.vertices)} ${tuple(b.cells)} simpleGrading (1 1 1)`).join('\n') +
    '\n);\nedges ();\nboundary\n(\n' + Object.entries(g.patches).map(([name, faces]) =>
      ` ${name} { type ${patchTypes[name]}; faces (${faces.map(tuple).join(' ')}); }`).join('\n') +
    '\n);\nmergePatchPairs ();\n';
}

export function expectedInlet(name) {
  const [inner, outer] = name === 'loxinlet' ? [0, 0.0025] : [0.0028, 0.005];
  const area = (outer ** 2 - inner ** 2) * Math.sin(2 * recipe.halfAngle_deg * Math.PI / 180) / 2;
  return { minRadius: inner, maxRadius: outer, area,
    fullAnnulusArea: Math.PI * (outer ** 2 - inner ** 2),
    wedgeAreaFraction: Math.sin(2 * recipe.halfAngle_deg * Math.PI / 180) / (2 * Math.PI) };
}
