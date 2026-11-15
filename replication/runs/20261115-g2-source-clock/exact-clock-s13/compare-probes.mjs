import fs from 'node:fs';
const [a,b,out]=process.argv.slice(2);function read(p){const lines=fs.readFileSync(p,'utf8').trim().split('\n'),head=lines.shift().split(',');return lines.map(l=>Object.fromEntries(l.split(',').map((v,i)=>[head[i],v])));}
const x=read(a),y=read(b);if(x.length!==20||y.length!==20)throw Error('20 executed source rows required');
let worst=0;for(let i=0;i<x.length;i++){if(x[i].passed!=='1'||y[i].passed!=='1')throw Error('Source identity failed');for(const k of Object.keys(x[i]).filter(k=>k!=='mode')){const u=Number(x[i][k]),v=Number(y[i][k]);if(!Number.isFinite(u+v))throw Error('Nonfinite:'+k);worst=Math.max(worst,Math.abs(u-v));if(u!==v)throw Error('Identical alpha parity failed:'+k);}}
fs.writeFileSync(out,JSON.stringify({executedRows:40,identicalAlphaBitwiseNumericParity:true,worstDifference:worst,CFDsteps:0,physicalValidation:false},null,2)+'\n');
