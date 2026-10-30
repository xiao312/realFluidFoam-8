// Numeric OpenFOAM sampled-set CSVs; no interpolation or guessed field order.
export function readCsv(text, label) {
  const lines = text.trim().split(/\r?\n/).filter(line => line.trim() && !line.trim().startsWith('#'));
  if (lines.length < 2) throw new Error(`Empty numeric CSV: ${label}`);
  const names = lines[0].split(',').map(name => name.trim().replace(/^"|"$/g, ''));
  if (new Set(names).size !== names.length || names.some(name => !name) ||
      ['x', 'y', 'z'].some(key => !names.includes(key))) throw new Error(`Ambiguous/missing coordinate headers: ${label}`);
  return lines.slice(1).map((line, index) => {
    const cells = line.split(',').map(cell => cell.trim());
    const values = cells.map(Number);
    if (cells.length !== names.length || cells.some(value => !value) || values.some(value => !Number.isFinite(value))) {
      throw new Error(`Ragged/nonfinite numeric CSV ${label} row ${index+2}`);
    }
    return Object.fromEntries(names.map((name, i) => [name, values[i]]));
  });
}

export function mergeFields(tables) {
  if (!tables.length || !tables[0].length) throw new Error('No sample rows');
  const rows = tables[0].map(row => ({ ...row }));
  for (const table of tables.slice(1)) {
    if (table.length !== rows.length) throw new Error('Split files have different sample counts');
    table.forEach((sample, i) => {
      if (['x', 'y', 'z'].some(key => sample[key] !== rows[i][key])) throw new Error('Split files have different coordinates');
      for (const [key, value] of Object.entries(sample)) {
        if (key in rows[i] && rows[i][key] !== value) throw new Error(`Conflicting split field ${key}`);
        rows[i][key] = value;
      }
    });
  }
  const positions = new Set(rows.map(row => JSON.stringify([row.x, row.y, row.z])));
  if (positions.size !== rows.length) throw new Error('Duplicate spatial sample coordinates');
  return rows;
}

export function writeCsv(rows) {
  if (!rows.length) throw new Error('No output rows');
  const columns = Object.keys(rows[0]);
  return [columns.join(','), ...rows.map(row => columns.map(key => row[key]).join(','))].join('\n')+'\n';
}
