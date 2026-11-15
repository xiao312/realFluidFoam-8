import fs from 'node:fs';import crypto from 'node:crypto';
const build=process.argv[2],sha=x=>crypto.createHash('sha256').update(x).digest('hex'),q=JSON.parse(fs.readFileSync(build+'/build-qualification.json'));
if(q.source!=='d020b8df0d7ba6c9fd2306770bb08f08d5292773'||!q.compile_link_help_passed||q.custom_library_count!==15)throw Error('Exact qualified clock build required');for(const p of q.products)if(sha(fs.readFileSync(build+'/'+p.file))!==p.sha256)throw Error('Product changed:'+p.file);
const parity=JSON.parse(fs.readFileSync('/workspace/results/source-clock-s01/parity.json'));if(!parity.identicalAlphaBitwiseNumericParity||parity.executedRows!==40)throw Error('Source parity not qualified');console.log(JSON.stringify({qualification:q,sourceParity:parity,scientificAcceptance:false}));
