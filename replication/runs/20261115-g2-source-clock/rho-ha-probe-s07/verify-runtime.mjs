import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root=process.argv[2],raw=readFileSync(`${root}/build-qualification.json`),r=JSON.parse(raw);
const hash=x=>createHash('sha256').update(x).digest('hex');
if(r.source!=='51075d584e7a9bb12a85201b6dcc4eae55303b52'||!r.compile_link_help_passed||r.custom_library_count!==15||!r.allCustomLibrariesRebuilt)throw Error('Unexpected compiled source/runtime');
for(const p of r.products)if(hash(readFileSync(`${root}/${p.file}`))!==p.sha256)throw Error(`Product hash mismatch:${p.file}`);
console.log(JSON.stringify({source:r.source,receiptSha256:hash(raw),products:r.products,scope:'Actual product identity and compilation only; physical checks follow',scientificAcceptance:false},null,2));
