import { readFile, copyFile, mkdir } from 'node:fs/promises';
import { digest } from '../../fgm-of8/direct-verification/physical-input.mjs';

const registeredManifest = 'a9407929f9559bf2bf6b2082acc4c0e05d9aeaa721abd645ceedc3ed1999ca70';
const fileNames = ['boundary', 'points', 'faces', 'owner', 'neighbour', 'pointZones', 'faceZones', 'cellZones'];
// Adapted from the retained mesh-contract-check.py and patch-flux-integrate.py.
// This exact registered asset uses OF7 binary compact faces, little-endian
// int32 labels and float64 points. Hash verification precedes interpretation.
function binaryList(raw) {
  if (!/format\s+binary\s*;/.test(raw.subarray(0, 1400).toString('latin1'))) throw new Error('Registered binary mesh expected');
  const match = /\n(\d+)\s*\n?\(/.exec(raw.subarray(600, 1400).toString('latin1'));
  if (!match) throw new Error('Cannot locate registered binary mesh list');
  return { count: Number(match[1]), offset: 600 + match.index + match[0].length };
}
function binaryOffset(raw, offset, bytes) {
  if (raw[offset + bytes] === 41) return offset;
  if (raw[offset] === 10 && raw[offset + 1 + bytes] === 41) return offset + 1;
  throw new Error('Binary mesh block length or terminator mismatch');
}
function readPoints(raw) {
  const list = binaryList(raw), offset = binaryOffset(raw, list.offset, list.count * 24);
  const points = new Float64Array(list.count * 3);
  for (let i = 0; i < points.length; i++) {
    points[i] = raw.readDoubleLE(offset + i * 8);
    if (!Number.isFinite(points[i])) throw new Error('Nonfinite mesh point');
  }
  return { count: list.count, points };
}
function readFaces(raw, pointCount) {
  const list = binaryList(raw), offset = binaryOffset(raw, list.offset, list.count * 4);
  const offsets = new Int32Array(list.count);
  for (let i = 0; i < offsets.length; i++) offsets[i] = raw.readInt32LE(offset + i * 4);
  const separatorOffset = offset + list.count * 4;
  const separator = /^\)\s*(\d+)\s*\(/.exec(raw.subarray(separatorOffset, separatorOffset + 64).toString('latin1'));
  if (!separator) throw new Error('Compact face separator absent');
  const count = Number(separator[1]);
  if (offsets[0] !== 0 || offsets.at(-1) !== count) throw new Error('Compact face offset/count mismatch');
  const flatOffset = binaryOffset(raw, separatorOffset + separator[0].length, count * 4);
  for (let i = 0; i < offsets.length - 1; i++) {
    if (offsets[i + 1] - offsets[i] < 3 || offsets[i + 1] > count) throw new Error('Invalid compact face offsets');
  }
  return { count: offsets.length - 1, face(index) {
    const labels = [];
    for (let j = offsets[index]; j < offsets[index + 1]; j++) {
      const label = raw.readInt32LE(flatOffset + j * 4);
      if (label < 0 || label >= pointCount) throw new Error('Out-of-range face point');
      labels.push(label);
    }
    return labels;
  } };
}

function boundaryGeometry(boundary, pointList, faceList) {
  const result = {};
  for (const match of boundary.toString().matchAll(/(\w+)\s*\{([^{}]*)\}/g)) {
    const count = /nFaces\s+(\d+)\s*;/.exec(match[2]);
    const start = /startFace\s+(\d+)\s*;/.exec(match[2]);
    if (!count || !start) continue;
    const patch = { type: /type\s+(\w+)\s*;/.exec(match[2])?.[1], faces: Number(count[1]),
      minX: Infinity, maxX: -Infinity, minRadius: Infinity, maxRadius: -Infinity, axialPlanes: [] };
    // The two wedge planes contain almost all boundary faces, but are not
    // injector surfaces. Do not walk 2*cells merely to infer the lip location.
    if (patch.type === 'wedge') {
      result[match[1]] = { type: patch.type, faces: patch.faces, inspected: false,
        reason: 'Azimuthal wedge plane excluded from injector-surface audit' };
      continue;
    }
    const planes = new Map();
    for (let face = Number(start[1]); face < Number(start[1]) + patch.faces; face++) {
      const vertices = faceList.face(face).map(n => Array.from(pointList.points.slice(n * 3, n * 3 + 3)));
      let minX = Infinity, maxX = -Infinity, minR = Infinity, maxR = -Infinity;
      for (const [x, y, z] of vertices) {
        minX = Math.min(minX, x); maxX = Math.max(maxX, x);
        const r = Math.hypot(y, z); minR = Math.min(minR, r); maxR = Math.max(maxR, r);
      }
      patch.minX = Math.min(patch.minX, minX); patch.maxX = Math.max(patch.maxX, maxX);
      patch.minRadius = Math.min(patch.minRadius, minR); patch.maxRadius = Math.max(patch.maxRadius, maxR);
      // Compact face-plane audit. Only genuinely near-constant-x faces qualify;
      // sloped/chamber surfaces are not forced into an injection plane.
      if (maxX - minX <= 1e-8) {
        let axialArea = 0;
        const first = vertices[0];
        for (let i = 1; i < vertices.length - 1; i++) {
          axialArea += ((vertices[i][1] - first[1]) * (vertices[i + 1][2] - first[2]) -
            (vertices[i][2] - first[2]) * (vertices[i + 1][1] - first[1])) / 2;
        }
        if (Math.abs(axialArea) <= 1e-20) continue;
        const key = Math.round((minX + maxX) / 2 / 1e-8);
        if (!planes.has(key)) planes.set(key, { groupedX_m: key * 1e-8, minX, maxX,
          minRadius: minR, maxRadius: maxR, faces: 0, signedAxialArea_m2: 0, absoluteAxialArea_m2: 0 });
        const plane = planes.get(key);
        plane.faces++; plane.signedAxialArea_m2 += axialArea; plane.absoluteAxialArea_m2 += Math.abs(axialArea);
        plane.minX = Math.min(plane.minX, minX); plane.maxX = Math.max(plane.maxX, maxX);
        plane.minRadius = Math.min(plane.minRadius, minR); plane.maxRadius = Math.max(plane.maxRadius, maxR);
      }
    }
    patch.axialPlanes = [...planes.values()].sort((a, b) => a.groupedX_m - b.groupedX_m);
    if (!patch.faces) patch.minX = patch.maxX = patch.minRadius = patch.maxRadius = null;
    result[match[1]] = patch;
  }
  return { coordinateUnits: 'm', axialPlaneGrouping_m: 1e-8, patches: result,
    paperAxialOrigin_m: null, interpretation: 'Measured non-wedge boundary geometry only. A paper-origin transform requires injector-surface interpretation and a cited drawing.' };
}

export async function inspectMesh(root, options = {}) {
  const manifestRaw = await readFile(`${root}/manifest.json`);
  if (digest(manifestRaw) !== registeredManifest) throw new Error('Mesh is not the registered immutable asset');
  const manifest = JSON.parse(manifestRaw);
  const buffers = {}, files = [];
  for (const name of fileNames) {
    const raw = await readFile(`${root}/polyMesh/${name}`);
    const expected = manifest.files.find(row => row.path === name);
    if (!expected || digest(raw) !== expected.sha256 || raw.length !== expected.bytes) throw new Error(`Mesh hash mismatch: ${name}`);
    files.push({ name, sha256: expected.sha256, bytes: raw.length });
    if (['boundary', 'points', 'faces'].includes(name)) buffers[name] = raw;
  }
  const patches = {};
  for (const match of buffers.boundary.toString().matchAll(/(\w+)\s*\{([^{}]*)\}/g)) {
    if (!['ch4inlet', 'loxinlet'].includes(match[1])) continue;
    const count = /nFaces\s+(\d+)\s*;/.exec(match[2]);
    const start = /startFace\s+(\d+)\s*;/.exec(match[2]);
    if (!count || !start) throw new Error(`Malformed inlet patch ${match[1]}`);
    patches[match[1]] = { startFace: Number(start[1]), faces: Number(count[1]), area: 0,
      axialArea: 0, lateralArea: 0, maxFaceLateralRatio: 0,
      minRadius: Infinity, maxRadius: 0, minX: Infinity, maxX: -Infinity };
  }
  if (!patches.ch4inlet || !patches.loxinlet) throw new Error('Required inlet patches absent');
  const pointList = readPoints(buffers.points), points = pointList.points;
  const faceList = readFaces(buffers.faces, pointList.count);
  if (pointList.count !== manifest.counts.points || faceList.count !== manifest.counts.faces) throw new Error('Registered mesh count mismatch');
  for (const patch of Object.values(patches)) {
    if (patch.startFace < 0 || patch.startFace + patch.faces > faceList.count) throw new Error('Patch face range invalid');
    for (let faceIndex = patch.startFace; faceIndex < patch.startFace + patch.faces; faceIndex++) {
      const labels = faceList.face(faceIndex);
      const vertices = labels.map(n => Array.from(points.slice(n * 3, n * 3 + 3)));
      for (const [x, y, z] of vertices) {
        const radius = Math.hypot(y, z);
        patch.minRadius = Math.min(patch.minRadius, radius); patch.maxRadius = Math.max(patch.maxRadius, radius);
        patch.minX = Math.min(patch.minX, x); patch.maxX = Math.max(patch.maxX, x);
      }
      const area = [0, 0, 0], first = vertices[0];
      for (let j = 1; j < vertices.length - 1; j++) {
        const a = vertices[j].map((v, k) => v - first[k]), b = vertices[j + 1].map((v, k) => v - first[k]);
        area[0] += (a[1] * b[2] - a[2] * b[1]) / 2;
        area[1] += (a[2] * b[0] - a[0] * b[2]) / 2;
        area[2] += (a[0] * b[1] - a[1] * b[0]) / 2;
      }
      const magnitude = Math.hypot(...area), lateral = Math.hypot(area[1], area[2]);
      if (!(magnitude > 0) || area[0] >= 0) throw new Error(`Invalid inward-facing or degenerate inlet face ${faceIndex}`);
      // The registered last O2 face has a measured 5.25e-11 m CAD offset:
      // tiny faces need not have normals identical to x at relative 1e-6.
      // Use actual face area, as flowRateInletVelocity does, and retain tilt.
      patch.area += magnitude;
      patch.axialArea += Math.abs(area[0]);
      patch.lateralArea += lateral;
      patch.maxFaceLateralRatio = Math.max(patch.maxFaceLateralRatio, lateral / Math.abs(area[0]));
    }
  }
  for (const patch of Object.values(patches)) {
    patch.aggregateLateralRatio = patch.lateralArea / patch.axialArea;
    if (patch.aggregateLateralRatio > 1e-6 || patch.maxX - patch.minX > 1e-8) throw new Error('Registered inlet plane geometry is inconsistent');
    patch.fullAnnulusArea = Math.PI * (patch.maxRadius ** 2 - patch.minRadius ** 2);
    patch.wedgeAreaFraction = patch.area / patch.fullAnnulusArea;
    if (!(patch.wedgeAreaFraction > 0 && patch.wedgeAreaFraction < 1)) throw new Error('Invalid measured wedge area fraction');
  }
  return { schema: 'registered-g2-mesh-inlet-audit-v1', manifestSha256: registeredManifest,
    meshSha256: manifest.mesh_sha256, pointCount: pointList.count, faceCount: faceList.count,
    cellCount: manifest.counts.cells,
    patches, files, paperGeometryQualified: false,
    ...(options.boundaryGeometry ? { boundaryGeometry: boundaryGeometry(buffers.boundary, pointList, faceList) } : {}) };
}

export async function copyMesh(root, out) {
  await mkdir(`${out}/constant/polyMesh`);
  for (const name of fileNames) await copyFile(`${root}/polyMesh/${name}`, `${out}/constant/polyMesh/${name}`);
}
