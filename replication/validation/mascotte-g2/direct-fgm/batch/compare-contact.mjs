import { readFile, writeFile } from 'node:fs/promises';
const [serial, parallel, output] = process.argv.slice(2);
if (!serial || !parallel || !output) throw new Error('Use compare-contact.mjs SERIAL MPI OUTPUT.json');
const a = JSON.parse(await readFile(`${serial}/verification.json`, 'utf8'));
const b = JSON.parse(await readFile(`${parallel}/verification.json`, 'utf8'));
if (a.kind !== 'contact' || b.kind !== 'contact' || a.status !== 'pass' || b.status !== 'pass') throw new Error('Both fresh contact checks must pass');
const x = a.analytical.profile, y = b.analytical.profile;
if (x.length !== y.length || x.some((p, i) => p.x !== y[i].x)) throw new Error('Reconstructed contact grids do not match');
const errors = x.map((p, i) => Math.abs(p.computed - y[i].computed));
const maximum = Math.max(...errors), rms = Math.sqrt(errors.reduce((s, e) => s + e * e, 0) / errors.length);
const result = { schema: 'forge-serial-mpi-contact-v1', ranks: 4, cells: x.length,
  maximumAbsoluteZDifference: maximum, rmsAbsoluteZDifference: rms, tolerance: 1e-8,
  status: Number.isFinite(maximum) && maximum <= 1e-8 ? 'pass' : 'fail',
  qualification: 'Discrete serial/MPI agreement for the matched fresh contact case; not G2 science acceptance' };
await writeFile(output, JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result, null, 2));
if (result.status !== 'pass') process.exitCode = 3;
