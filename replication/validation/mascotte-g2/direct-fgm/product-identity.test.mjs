import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {verifyProductBytes} from './product-identity.mjs';
test('full and inherited receipts retain exact byte identity',()=>{
  const raw=Buffer.from('qualified library'), sha256=createHash('sha256').update(raw).digest('hex');
  const p={file:'lib/libODE.so',sha256};
  assert.equal(verifyProductBytes({...p,bytes:raw.length},raw).bytes,raw.length);
  const inherited={...p,reused:true,resolved:'/workspace/build/parent/lib/libODE.so'};
  assert.equal(verifyProductBytes(inherited,raw).inherited,true);
  assert.throws(()=>verifyProductBytes(inherited,Buffer.from('changed library')));
  assert.throws(()=>verifyProductBytes({...p,bytes:raw.length+1},raw));
  assert.throws(()=>verifyProductBytes(p,raw));
  assert.throws(()=>verifyProductBytes({...inherited,bytes:-1},raw));
});
