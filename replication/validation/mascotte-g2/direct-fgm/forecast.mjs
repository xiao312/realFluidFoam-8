import { createReadStream } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { createInterface } from 'node:readline';
import { resolve } from 'node:path';

const [casePath, ...args] = process.argv.slice(2);
if (!casePath || args.length % 2) throw new Error('Use forecast.mjs CASE [--durations 0.0001,0.001] [--ranks 16,32]');
const options = {};
for (let i = 0; i < args.length; i += 2) {
  if (!['--durations', '--ranks'].includes(args[i])) throw new Error(`Unknown option ${args[i]}`);
  options[args[i]] = args[i + 1].split(',').map(Number);
}
const root = resolve(casePath), manifest = JSON.parse(await readFile(`${root}/direct-g2-input.json`, 'utf8'));
const durations = options['--durations'] ?? [1e-4, 1e-3, manifest.convectiveTimes_s.axial50mm, manifest.convectiveTimes_s.chamber200mm];
const ranks = options['--ranks'] ?? [manifest.ranks, 16, 32];
if (durations.some(t => !Number.isFinite(t) || t <= 0) || ranks.some(n => !Number.isInteger(n) || n < 1 || n > 64)) throw new Error('Invalid durations/ranks');
let time = null, deltaT = null, totalSteps = 0;
const records = [];
for await (const line of createInterface({ input: createReadStream(`${root}/log.solver`), crlfDelay: Infinity })) {
  let match;
  if ((match = /^Time =\s+(\S+)/.exec(line))) time = Number(match[1]);
  if ((match = /^deltaT =\s+(\S+)/.exec(line))) deltaT = Number(match[1]);
  if ((match = /^ExecutionTime =\s+(\S+)\s+s\s+ClockTime =\s+(\S+)\s+s/.exec(line)) && time !== null) {
    const row = { time, cpu: Number(match[1]), wall: Number(match[2]), deltaT };
    if (![row.time, row.cpu, row.wall].every(Number.isFinite)) throw new Error('Invalid clock record');
    if (records.length && row.time <= records.at(-1).time) throw new Error('Nonmonotone solver times; concatenated/restarted logs are not a clean-start forecast');
    totalSteps++;
    records.push(row);
    if (records.length > 101) records.shift();
  }
}
const first = records[0], last = records.at(-1);
if (records.length < 3 || !(last.wall > first.wall) || !(last.time > first.time)) {
  console.log(JSON.stringify({ status: 'insufficient measured progress', completedSteps: totalSteps, retainedClockRecords: records.length,
    interpretation: 'No timing or scaling estimate until actual solver advancement has measurable wall time.' }, null, 2));
  process.exit(2);
}
const wallPerPhysicalSecond = (last.wall - first.wall) / (last.time - first.time);
const meanStep = (last.time - first.time) / (records.length - 1);
const cells = manifest.mesh.cellCount ?? null;
const projections = durations.map(duration_s => ({ duration_s, startsFromZero: true,
  estimatedSteps: duration_s / meanStep,
  atMeasuredRanks: { ranks: manifest.ranks, computeWall_s: duration_s * wallPerPhysicalSecond,
    allocatedCoreHours: duration_s * wallPerPhysicalSecond * manifest.ranks / 3600 },
  idealScalingBounds: ranks.map(n => ({ ranks: n, computeWall_s: duration_s * wallPerPhysicalSecond * manifest.ranks / n,
    cellsPerRank: cells === null ? null : cells / n, measuredSpeedup: false })),
}));
console.log(JSON.stringify({ schema: 'forge-g2-cost-forecast-v1', case: root,
  sourceInputHashes: manifest.inputHashes, completedSteps: totalSteps,
  observed: { startTime_s: first.time, endTime_s: last.time, elapsedWall_s: last.wall - first.wall,
    steps: records.length - 1, ranks: manifest.ranks, cellCount: cells, meanStep_s: meanStep,
    latestStep_s: last.deltaT, wallPerPhysicalSecond }, projections,
  limitations: ['Uses only the last completed steps; timestep collapse, nonlinear stiffness and later flow development can change cost.',
    'Excludes image preparation, compilation, scheduler queue, reconstruction and cleanup.',
    'Rank projections assume perfect scaling and are optimistic bounds, not promises. Measure 4/16/32-rank fresh cases before choosing a long run.',
    'No run, continuation, budget change or admission is performed.'] }, null, 2));
