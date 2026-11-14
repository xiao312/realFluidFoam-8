import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const [root,dest,action]=process.argv.slice(2);if(!root||!dest||![undefined,'--apply'].includes(action))throw Error('Use SOURCE NEW_DEST [--apply]');
const original=path.join(root,'applications/solvers/realFluidFoam');if(fs.existsSync(dest))throw Error('Destination already exists');
const sha=s=>crypto.createHash('sha256').update(s).digest('hex'),changes=[];
function patch(name,transform){const before=fs.readFileSync(path.join(original,name),'utf8');const after=transform(before);if(before===after)throw Error('No patch: '+name);changes.push({name,before,after,beforeSha256:sha(before),afterSha256:sha(after)});}
patch('Make/files',s=>{if(!s.includes('$(FOAM_USER_APPBIN)/realFluidFoam'))throw Error('Unexpected executable');return s.replace('$(FOAM_USER_APPBIN)/realFluidFoam','$(FOAM_USER_APPBIN)/realFluidFoamAudited');});
patch('EEqn.H',s=>{if((s.match(/thermo\.correct\(\);/g)||[]).length!==1)throw Error('Unexpected energy body');return s.replace('thermo.correct();','thermo.correct();\n    auditFgmThermoClosure(thermo);');});
patch('realFluidFoam.C',s=>{if(!s.includes('#include "fvcSmooth.H"')||!s.includes('    turbulence->validate();')||!s.includes('        runTime.write();'))throw Error('Unexpected author main');return s.replace('#include "fvcSmooth.H"','#include "fvcSmooth.H"\n#include "fgmThermoClosure.H"').replace('    turbulence->validate();','    Info().precision(15);\n    turbulence->validate();\n    auditFgmThermoClosure(thermo);').replace('        runTime.write();',`        auditFgmThermoClosure(thermo, false);
        Info<< "AUTHOR_REFERENCE_STATE t=" << runTime.value()
            << " pMin_Pa=" << gMin(p.primitiveField()) << " pMax_Pa=" << gMax(p.primitiveField())
            << " TMin_K=" << gMin(T.primitiveField()) << " TMax_K=" << gMax(T.primitiveField())
            << " massKg=" << fvc::domainIntegrate(rho).value()
            << " totalSensibleEnergyJ=" << fvc::domainIntegrate(rho*(thermo.he()+K)-p).value() << endl;
        runTime.write();`);});
const audit=fs.readFileSync(path.join(root,'applications/solvers/reactingFoamSolveZ/fgmThermoClosure.H'));
if(action){if(!process.env.SLURM_JOB_ID)throw Error('Allocated preparation required');fs.cpSync(original,dest,{recursive:true,errorOnExist:true});for(const c of changes)fs.writeFileSync(path.join(dest,c.name),c.after);fs.writeFileSync(path.join(dest,'fgmThermoClosure.H'),audit);}
console.log(JSON.stringify({readOnly:!action,sourceRoot:root,destination:dest,equationsChanged:false,caloricAuditSha256:sha(audit),patches:changes.map(({before,after,...r})=>r),scientificAcceptance:false},null,2));
