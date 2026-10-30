import { readFile, writeFile, readdir, access } from 'node:fs/promises';
import { resolve, join, relative, isAbsolute } from 'node:path';
import { createHash } from 'node:crypto';
const [directory, mode='--plan'] = process.argv.slice(2);
if (!directory || !['--plan','--apply'].includes(mode)) throw new Error('Use bind-table.mjs NEW_CASE --plan|--apply');
const root=resolve(directory), path=join(root,'constant','combustionProperties');
const raw=await readFile(path), text=raw.toString();
const matches=[...text.matchAll(/\btable\s+"([^"\r\n]+)"\s*;/g)];
if(matches.length!==1)throw new Error('Exactly one quoted table entry is required');
const entry=matches[0], candidate=isAbsolute(entry[1])?resolve(entry[1]):resolve(root,'constant',entry[1]);
const within=relative(join(root,'constant'),candidate);
if(!within || within.startsWith('..') || isAbsolute(within))throw new Error('Only a table inside this case constant directory may be bound');
const table=await readFile(candidate), absolute=candidate.replaceAll('\\','/');
const after=text.slice(0,entry.index)+`table "${absolute}";`+text.slice(entry.index+entry[0].length);
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const receipt={schema:'case-owned-fgm-table-binding/v1',case:root,table:absolute,tableSha256:hash(table),
 dictionaryBeforeSha256:hash(raw),dictionaryAfterSha256:hash(after),physicalBytesChanged:false};
if(mode==='--plan'){console.log(JSON.stringify({dryRun:true,...receipt},null,2));process.exit(0);}
if(!process.env.SLURM_JOB_ID)throw new Error('Table binding requires its admitted allocation');
const entries=await readdir(root);
if(!entries.includes('0')||entries.some(name=>/^processor\d+$/.test(name)||(/^\d/.test(name)&&Number(name)!==0&&Number.isFinite(Number(name)))))throw new Error('Bind only fresh undecomposed time-zero cases');
const target=join(root,'table-binding.json');
try{await access(target);throw new Error('Table binding already exists');}catch(error){if(error.code!=='ENOENT')throw error;}
await writeFile(path,after);
await writeFile(target,JSON.stringify({...receipt,jobId:process.env.SLURM_JOB_ID},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(receipt,null,2));
