import test from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { mergeFiles } from './samples.mjs';

test('OF8 numeric vector components join scalar density by exact coordinate', () => {
  // Writer-format fixture only, not CFD data. Vector file intentionally reverses rows.
  const files = ['nearAxis_U.csv', 'nearAxis_T_rho.csv'].map(name =>
    fileURLToPath(new URL('./fixtures/' + name, import.meta.url)));
  const data = mergeFiles(files);
  assert.deepEqual(data.fields, ['T', 'U_0', 'U_1', 'U_2', 'rho']);
  assert.deepEqual(data.rows.map(row => [row.x, row.U_0, row.rho]),
    [[.001, 2, 2], [.002, 4, 1]]);
});
