// Accept both valid OpenFOAM spellings; change bookkeeping, not coefficients.
export function withInertSpecies(dictionary, name) {
  if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(name)) throw Error('Explicit inert species name required');
  const entry = /\binertSpecie\s+(?:"[^"\r\n;]+"|[A-Za-z0-9_]+)\s*;/g;
  if ((dictionary.match(entry) ?? []).length !== 1) throw Error('Exactly one explicit inertSpecie required');
  return dictionary.replace(entry, 'inertSpecie '+name+';');
}
