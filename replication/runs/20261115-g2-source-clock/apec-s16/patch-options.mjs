import fs from 'node:fs';
const root=process.argv[2];
for(const module of ['replication/validation/schmitt-contact','replication/validation/schmitt-contact/apec']){
 const file=root+'/'+module+'/Make/options';let s=fs.readFileSync(file,'utf8');
 if(!s.includes('EXE_INC =')||!s.includes('EXE_LIBS ='))throw Error(file);
 s=s.replace('EXE_INC =','EXE_INC = -isystem "/usr/include/x86_64-linux-gnu" -B"/usr/lib/x86_64-linux-gnu/"').replace('EXE_LIBS =','EXE_LIBS = -B"/usr/lib/x86_64-linux-gnu/"');
 fs.writeFileSync(file,s);
}
