import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const [directory, logPath, receiptPath] = process.argv.slice(2);
if (!directory || !logPath || !receiptPath) throw new Error('Use allow-physical-diagnostic.mjs CASE LOG NEW_RECEIPT');
const raw = await readFile(`${directory}/verification.json`), result = JSON.parse(raw);
const logRaw = await readFile(logPath), log = logRaw.toString();
if (result.kind !== 'physical-conversion' || result.status !== 'fail') throw new Error('Exception requires the failed physical closed case');
const failures = result.checks.filter(row => !row.pass).map(row => row.name).sort();
const expected = ['assembled_equation_relative_residual', 'legacy_residual_duplicate_identity_W'].sort();
if (JSON.stringify(failures) !== JSON.stringify(expected)) throw new Error(`Different failure scope: ${failures}`);
for (const name of ['initial_time_zero','reached_end_time','mass_relative_drift','coupled_residual_audit_present',
 'total_energy_error_per_chemical_change','no_table_Q_in_absolute_energy_equation',
 'pressure_drift_from_fixed_table_pressure','physical_progress_changed','no_lookup_clipping']) {
 if (!result.checks.some(row => row.name === name && row.pass && Number.isFinite(row.measured))) throw new Error(`Missing passed ${name}`);
}
if (!/\nEnd\s*(?:\n|$)/.test(log) || /FOAM FATAL|Floating point exception/.test(log)) throw new Error('Run did not terminate normally');
function records(label) {
 return log.split(/\r?\n/).filter(line => line.startsWith(label+' ')).map(line =>
  Object.fromEntries([...line.matchAll(/(\w+)=([^\s]+)/g)].map(([,k,v])=>[k,Number(v)])));
}
const equations = records('energyEquation'), audit = records('energyResidualAudit');
if (!audit.length || audit.length !== equations.length || audit.length !== result.equationCount) throw new Error('Missing complete fresh arithmetic audit');
let maximumResidualFraction = 0, maximumIdentityFraction = 0, maximumSummandScaleW = 0;
for (let i=0;i<audit.length;i++) {
 const a=audit[i], e=equations[i], n=a.arithmeticOperationsPerCell;
 if (!Number.isInteger(n) || n<3 || n>1000 || !(a.matrixSummandL1W>0) || a.t!==e.t) throw new Error('Invalid measured matrix arithmetic');
 const unit=Number.EPSILON/2, bound=n*unit/(1-n*unit)*a.matrixSummandL1W;
 if (!Number.isFinite(bound) || Math.abs(a.residualArithmeticBoundW/bound-1)>1e-12) throw new Error('Logged gamma_n bound does not reproduce');
 const residualFraction=e.residualL1W/bound, identityFraction=a.duplicateIdentityErrorL1W/(3*bound);
 if (![residualFraction,identityFraction].every(v=>Number.isFinite(v)&&v>=0&&v<=1)) throw new Error(`Residual exceeds stored-matrix arithmetic bound at record ${i}`);
 maximumResidualFraction=Math.max(maximumResidualFraction,residualFraction);
 maximumIdentityFraction=Math.max(maximumIdentityFraction,identityFraction);
 maximumSummandScaleW=Math.max(maximumSummandScaleW,a.matrixSummandL1W);
}
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const receipt={schema:'bounded-physical-diagnostic-exception/v1',permittedAction:'subsequent bounded G2 diagnostic only',
 originalVerdict:'fail',thresholdsUnchanged:true,scientificAcceptance:false,independentApproval:false,
 verificationSha256:hash(raw),solverLogSha256:hash(logRaw),failedChecks:failures,
 measuredRecords:audit.length,maximumResidualFractionOfArithmeticBound:maximumResidualFraction,
 maximumIdentityFractionOfThreeArithmeticBounds:maximumIdentityFraction,maximumSummandScaleW,
 basis:'Actual stored matrix summands and gamma_n residual-evaluation rounding bound; all independent conservation/pressure/coverage checks pass. This is not a physical-accuracy waiver.'};
await writeFile(receiptPath,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(receipt,null,2));
