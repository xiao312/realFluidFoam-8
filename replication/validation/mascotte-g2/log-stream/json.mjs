import {open} from 'node:fs/promises';

function* encode(value,depth=0,ancestors=new Set()){
 if(value===null||typeof value!=='object'){
  const text=JSON.stringify(value);yield text===undefined?'null':text;return;
 }
 if(ancestors.has(value))throw Error('Cannot serialize a circular report');
 ancestors.add(value);
 const array=Array.isArray(value),keys=array?value.map((_,i)=>i):Object.keys(value).filter(k=>value[k]!==undefined);
 yield array?'[':'{';
 for(let i=0;i<keys.length;i++){
  const key=keys[i];yield (i?',\n':'\n')+'  '.repeat(depth+1);
  if(!array)yield JSON.stringify(key)+': ';
  yield* encode(value[key],depth+1,ancestors);
 }
 if(keys.length)yield '\n'+'  '.repeat(depth);
 yield array?']':'}';ancestors.delete(value);
}

export async function writeJson(path,value){
 const file=await open(path,'wx');let buffer='';
 async function flush(){
  const raw=Buffer.from(buffer);buffer='';let offset=0;
  while(offset<raw.length){const result=await file.write(raw,offset,raw.length-offset);if(!result.bytesWritten)throw Error('JSON write made no progress');offset+=result.bytesWritten;}
 }
 try{for(const chunk of encode(value)){buffer+=chunk;if(buffer.length>=65536)await flush();}buffer+='\n';await flush();}
 finally{await file.close();}
}
