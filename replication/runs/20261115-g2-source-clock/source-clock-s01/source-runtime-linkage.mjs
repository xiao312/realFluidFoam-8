import {basename} from 'node:path';

// ldd prints direct absolute dependencies without the usual "name => path".
// Return every entry; the caller verifies exact real paths and file hashes.
export function dynamicLibraries(text) {
  if (/not found/.test(text)) throw Error('Unresolved dynamic library');
  const entries=[];
  for (const line of text.split('\n')) {
    const arrow=/^\s*(\S+)\s+=>\s+(\/\S+)/.exec(line);
    const direct=/^\s*(\/\S+)\s+\(/.exec(line);
    if (arrow) entries.push({name:arrow[1],path:arrow[2]});
    else if (direct) entries.push({name:basename(direct[1]),path:direct[1]});
  }
  return entries;
}
