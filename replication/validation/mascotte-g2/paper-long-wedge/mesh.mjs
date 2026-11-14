import { readFile, readdir, mkdir, copyFile } from 'node:fs/promises';
import { mode, recipe, recipeSha256, blockMeshDictionary, expectedCounts,
  expectedPatchFaces, patchTypes, expectedInlet, digest } from './recipe.mjs';
import { parsePoints, parseFaces, parseLabels, parseBoundary, faceArea } from '../coarse-wedge/ascii-mesh.mjs';

export const meshFiles = ['boundary', 'points', 'faces', 'owner', 'neighbour'];
const optionalFiles = ['pointZones', 'faceZones', 'cellZones'];
function near(value, expected, tolerance, name) {
  if (!Number.isFinite(value) || Math.abs(value - expected) > tolerance) throw new Error(`${name}: ${value} differs from ${expected}`);
}
export async function readMesh(directory) {
  const listing = await readdir(directory);
  const files = [], buffers = {};
  for (const name of [...meshFiles, ...optionalFiles.filter(n => listing.includes(n))]) {
    const raw = await readFile(`${directory}/${name}`);
    buffers[name] = raw; files.push({ name, sha256: digest(raw), bytes: raw.length });
  }
  const points = parsePoints(buffers.points), faces = parseFaces(buffers.faces, points.length);
  const owners = parseLabels(buffers.owner), neighbours = parseLabels(buffers.neighbour);
  const patches = parseBoundary(buffers.boundary);
  if (points.length !== expectedCounts.points || faces.length !== expectedCounts.faces ||
      owners.length !== faces.length || neighbours.length !== expectedCounts.internalFaces) throw new Error('Paper-exit mesh count mismatch');
  const used = new Set();
  for (let i = 0; i < owners.length; i++) {
    if (owners[i] >= expectedCounts.cells) throw new Error('Owner cell outside recipe');
    used.add(owners[i]);
    if (i < neighbours.length && (neighbours[i] >= expectedCounts.cells || neighbours[i] <= owners[i])) throw new Error('Invalid internal face ownership');
  }
  if (used.size !== expectedCounts.cells) throw new Error('Missing cell ownership');
  for (const [x, y, z] of points) {
    const radius = Math.hypot(y, z), angle = Math.atan2(z, y) * 180 / Math.PI;
    if (x < -1e-12 || x > recipe.axialLength_m + 1e-12 || radius > .025 + 1e-12 || y < -1e-12) throw new Error('Point outside recipe');
    if (radius > 1e-14) near(Math.abs(angle), recipe.halfAngle_deg, 1e-9, 'Wedge point angle');
  }
  if (Object.keys(patches).sort().join() !== Object.keys(patchTypes).sort().join()) throw new Error('Patch names differ from recipe');
  let nextFace = neighbours.length, volume = 0;
  const closure = [0, 0, 0];
  for (const [name, patch] of Object.entries(patches)) {
    if (patch.type !== patchTypes[name] || patch.faces !== expectedPatchFaces[name] || patch.startFace !== nextFace) throw new Error(`Unexpected patch type/count/range: ${name}`);
    nextFace += patch.faces;
    Object.assign(patch, { area: 0, axialArea: 0, lateralArea: 0, minX: Infinity, maxX: -Infinity, minRadius: Infinity, maxRadius: -Infinity });
    for (let index = patch.startFace; index < nextFace; index++) {
      const vertices = faces[index].map(label => points[label]);
      const area = faceArea(vertices), magnitude = Math.hypot(...area);
      if (!(magnitude > 0)) throw new Error('Generated mesh contains a zero-area face');
      patch.area += magnitude; patch.axialArea += Math.abs(area[0]); patch.lateralArea += Math.hypot(area[1], area[2]);
      area.forEach((v, k) => { closure[k] += v; });
      // For planar faces any face point has the same dot product with its area vector.
      volume += vertices[0].reduce((v, coordinate, k) => v + coordinate * area[k], 0) / 3;
      for (const [x, y, z] of vertices) {
        const r = Math.hypot(y, z);
        patch.minX = Math.min(patch.minX, x); patch.maxX = Math.max(patch.maxX, x);
        patch.minRadius = Math.min(patch.minRadius, r); patch.maxRadius = Math.max(patch.maxRadius, r);
      }
      if (['loxinlet', 'ch4inlet'].includes(name) && area[0] >= 0) throw new Error('Inlet outward normal is not negative x');
    }
    if (!patch.faces) patch.minX = patch.maxX = patch.minRadius = patch.maxRadius = null;
  }
  if (nextFace !== faces.length) throw new Error('Boundary ranges do not cover all external faces');
  const expectedVolume = .5 * .025 ** 2 * Math.sin(5 * Math.PI / 180) * recipe.axialLength_m;
  near(volume, expectedVolume, expectedVolume * 1e-9, 'Mesh volume');
  if (Math.hypot(...closure) > 1e-12) throw new Error('Boundary surface is not closed');
  for (const name of ['loxinlet', 'ch4inlet']) {
    const patch = patches[name], expected = expectedInlet(name);
    near(patch.area, expected.area, expected.area * 1e-9, `${name} area`);
    near(patch.minRadius, expected.minRadius, 1e-12, `${name} inner radius`);
    near(patch.maxRadius, expected.maxRadius, 1e-12, `${name} outer radius`);
    near(patch.minX, 0, 1e-12, `${name} inlet plane`); near(patch.maxX, 0, 1e-12, `${name} inlet plane`);
    patch.fullAnnulusArea = expected.fullAnnulusArea;
    patch.wedgeAreaFraction = patch.area / patch.fullAnnulusArea;
    patch.aggregateLateralRatio = patch.lateralArea / patch.axialArea;
    near(patch.aggregateLateralRatio, 0, 1e-10, `${name} tilt`);
  }
  return { schema: 'paper-exit-g2-measured-mesh/v1', mode, recipeSha256,
    counts: { ...expectedCounts }, files, patches, volume_m3: volume, surfaceClosure_m2: closure,
    meshSha256: digest(JSON.stringify(files)), axisymmetricBoundaryType: 'empty',
    diagnosticAxialOrigin_m: 0, paperAxialOrigin_m: 0, upstreamDucts: false,
    matchedFeatures: recipe.matchedFeatures, omittedFeatures: recipe.omittedFeatures, paperGeometryQualified: false,
    interpretation: 'Paper exit-area diagnostic at x=0; upstream taper/ducts and square chamber omitted' };
}

export async function checkEvidence(root, dictionaryPath = 'blockMeshDict') {
  const dictionary = await readFile(`${root}/${dictionaryPath}`);
  if (digest(dictionary) !== digest(blockMeshDictionary())) throw new Error('Generated dictionary differs from fixed recipe');
  const recipeRaw = await readFile(`${root}/paper-exit-mesh-recipe.json`), recorded = JSON.parse(recipeRaw);
  if (recorded.mode !== mode || recorded.recipeSha256 !== recipeSha256 || recorded.dictionarySha256 !== digest(dictionary)) throw new Error('Recipe identity mismatch');
  const evidence = {};
  for (const name of ['log.blockMesh', 'log.checkMesh']) {
    const raw = await readFile(`${root}/${name}`), text = raw.toString();
    if (!/\nEnd\s*(?:\n|$)/.test(text) || /FOAM FATAL|Segmentation fault|Floating point exception/.test(text)) throw new Error(`Incomplete/failed ${name}`);
    if (name === 'log.checkMesh' && (!/Mesh OK\./.test(text) || /Failed \d+ mesh checks/.test(text))) throw new Error('checkMesh did not pass');
    evidence[name] = { sha256: digest(raw), bytes: raw.length };
  }
  return { recipeReceiptSha256: digest(recipeRaw), dictionarySha256: digest(dictionary), logs: evidence };
}

export async function inspectPaperExitMesh(root) {
  const raw = await readFile(`${root}/manifest.json`), manifest = JSON.parse(raw);
  if (manifest.schema !== 'paper-exit-g2-qualified-mesh-asset/v1' || manifest.mode !== mode || manifest.recipeSha256 !== recipeSha256) throw new Error('Not a qualified paper-exit diagnostic mesh asset');
  const evidence = await checkEvidence(root), mesh = await readMesh(`${root}/polyMesh`);
  if (JSON.stringify(manifest.files) !== JSON.stringify(mesh.files) || manifest.meshSha256 !== mesh.meshSha256 ||
      JSON.stringify(manifest.evidence) !== JSON.stringify(evidence)) throw new Error('Paper-exit mesh/evidence bytes changed after qualification');
  return { ...mesh, manifestSha256: digest(raw), pointCount: mesh.counts.points,
    faceCount: mesh.counts.faces, cellCount: mesh.counts.cells, evidence };
}
export async function copyPaperExitMesh(root, out) {
  const mesh = await inspectPaperExitMesh(root);
  await mkdir(`${out}/constant/polyMesh`);
  for (const file of mesh.files) await copyFile(`${root}/polyMesh/${file.name}`, `${out}/constant/polyMesh/${file.name}`);
}
