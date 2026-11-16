import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';

const options={files:[]};
for(let i=2;i<process.argv.length;i+=2){
  const flag=process.argv[i],value=process.argv[i+1];
  if(!value)throw Error('Use --bash BASH_EXE --file PAYLOAD [--file CHILD] [--out NEW_JSON]');
  if(flag==='--file')options.files.push(resolve(value));
  else if(flag==='--bash'&&!options.bash)options.bash=value;
  else if(flag==='--out'&&!options.out)options.out=resolve(value);
  else throw Error('Unknown or repeated option: '+flag);
}
if(!options.bash||!options.files.length||new Set(options.files).size!==options.files.length)
  throw Error('Explicit Bash and distinct payload files required');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const files=[];
for(const file of options.files){
  const raw=await readFile(file),lines=raw.toString().split(/\r?\n/);
  const shell=spawnSync(options.bash,['-n'],{input:raw,encoding:'utf8'});
  if(shell.error)throw Error('Cannot invoke declared Bash: '+shell.error.message);
  const blocks=[],errors=[];
  if(shell.status!==0)errors.push('Bash syntax failed; inspect retained payload');
  for(let i=0;i<lines.length;i++){
    const line=lines[i];
    if(!/(?:^|\s)node(?:\s|$)/.test(line)||!line.includes('<<'))continue;
    const match=line.match(/<<\s*'([A-Za-z_][A-Za-z_0-9]*)'\s*$/);
    if(!match){errors.push(`Unsupported Node heredoc at line${i+1}`);continue;}
    const delimiter=match[1],start=i+1,code=[];
    while(++i<lines.length&&lines[i]!==delimiter)code.push(lines[i]);
    if(i===lines.length){errors.push(`Unterminated Node heredoc at line${start}`);break;}
    const module=/--input-type(?:=|\s+)module(?:\s|$)/.test(line);
    const result=spawnSync(process.execPath,['--check','--input-type='+(module?'module':'commonjs')],
      {input:code.join('\n'),encoding:'utf8'});
    if(result.error)throw Error('Cannot invoke Node checker: '+result.error.message);
    const message=result.status===0?null:(result.stderr.split(/\r?\n/).find(s=>s.startsWith('SyntaxError:'))??'Node syntax check failed');
    blocks.push({commandLine:start,endLine:i+1,inputType:module?'module':'commonjs',
      codeSha256:hash(code.join('\n')),passed:result.status===0,error:message});
    if(message)errors.push(`Node block at line${start}: ${message}`);
  }
  files.push({file,sha256:hash(raw),bytes:raw.length,shellSyntaxPassed:shell.status===0,
    nodeBlocks:blocks,errors,passed:errors.length===0});
}
const report={schema:'science-payload-syntax-preflight/v1',files,
  passed:files.every(f=>f.passed),payloadsExecuted:false,physicalQualification:false,
  checkerSha256:hash(await readFile(new URL(import.meta.url))),nodeVersion:process.version};
if(options.out)await writeFile(options.out,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(report,null,2));
if(!report.passed)process.exitCode=1;
