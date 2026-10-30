// Deliberately narrow: blockMesh's ASCII points/faces/labels, not arbitrary Foam dictionaries.
function content(raw) {
  let text = raw.toString('utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\r\n]*/g, '');
  const header = /FoamFile\s*\{[^{}]*\}/.exec(text);
  if (!header || !/format\s+ascii\s*;/.test(header[0])) throw new Error('Coarse mesh requires ASCII Foam files');
  text = text.replace(header[0], '').trim();
  return text;
}
function list(raw) {
  const text = content(raw), match = /^(\d+)\s*\(/.exec(text);
  if (!match) throw new Error('Missing ASCII mesh list');
  const tokens = text.slice(match[0].length).match(/[()]|[^\s()]+/g) ?? [];
  let cursor = 0;
  return { count: Number(match[1]), take(expected) {
    const value = tokens[cursor++];
    if (value === undefined || (expected !== undefined && value !== expected)) throw new Error(`Malformed mesh token: expected ${expected}, got ${value}`);
    return value;
  }, done() {
    this.take(')');
    if (cursor !== tokens.length) throw new Error('Unexpected mesh data after list');
  } };
}
function integer(value) {
  if (!/^\d+$/.test(value)) throw new Error('Expected nonnegative mesh label');
  return Number(value);
}
export function parsePoints(raw) {
  const input = list(raw), values = [];
  for (let i = 0; i < input.count; i++) {
    input.take('(');
    const p = [Number(input.take()), Number(input.take()), Number(input.take())];
    if (!p.every(Number.isFinite)) throw new Error('Nonfinite mesh point');
    input.take(')'); values.push(p);
  }
  input.done(); return values;
}
export function parseFaces(raw, pointCount) {
  const input = list(raw), values = [];
  for (let i = 0; i < input.count; i++) {
    const count = integer(input.take());
    if (count < 3 || count > 4) throw new Error('Only collapsed wedge triangles and quadrilateral faces are expected');
    input.take('('); const face = [];
    for (let j = 0; j < count; j++) {
      const label = integer(input.take());
      if (label >= pointCount) throw new Error('Face point outside range');
      face.push(label);
    }
    if (new Set(face).size !== count) throw new Error('Repeated label in generated nondegenerate face');
    input.take(')'); values.push(face);
  }
  input.done(); return values;
}
export function parseLabels(raw) {
  const input = list(raw), values = [];
  for (let i = 0; i < input.count; i++) values.push(integer(input.take()));
  input.done(); return values;
}
export function parseBoundary(raw) {
  const text = content(raw), count = /^(\d+)\s*\(/.exec(text);
  if (!count) throw new Error('Boundary list absent');
  const patches = {};
  for (const match of text.matchAll(/(\w+)\s*\{([^{}]*)\}/g)) {
    const name = match[1], block = match[2];
    const type = /type\s+(\w+)\s*;/.exec(block)?.[1];
    const n = /nFaces\s+(\d+)\s*;/.exec(block)?.[1];
    const start = /startFace\s+(\d+)\s*;/.exec(block)?.[1];
    if (!type || n === undefined || start === undefined || patches[name]) throw new Error('Invalid boundary patch');
    patches[name] = { type, faces: Number(n), startFace: Number(start) };
  }
  if (Object.keys(patches).length !== Number(count[1])) throw new Error('Boundary count mismatch');
  return patches;
}
export function faceArea(vertices) {
  const area = [0, 0, 0], a = vertices[0];
  for (let j = 1; j < vertices.length - 1; j++) {
    const b = vertices[j].map((x, k) => x - a[k]), c = vertices[j + 1].map((x, k) => x - a[k]);
    area[0] += (b[1] * c[2] - b[2] * c[1]) / 2;
    area[1] += (b[2] * c[0] - b[0] * c[2]) / 2;
    area[2] += (b[0] * c[1] - b[1] * c[0]) / 2;
  }
  return area;
}
