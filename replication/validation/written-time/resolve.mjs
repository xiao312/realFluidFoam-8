import fs from 'node:fs';
import path from 'node:path';

export function resolveWrittenTimeDirectory({processorDirectory, physicalTime, precision, format}) {
  if (!Number.isFinite(physicalTime) || physicalTime < 0) {
    throw Error('Physical time must be finite and nonnegative');
  }
  if (!Number.isInteger(precision) || precision < 1 || precision > 17) {
    throw Error('Explicit case timePrecision from 1 to 17 required');
  }
  if (!['general', 'fixed', 'scientific'].includes(format)) {
    throw Error('Explicit case timeFormat general, fixed or scientific required');
  }
  const exponent = physicalTime === 0 ? 0 : Math.floor(Math.log10(physicalTime));
  // General precision counts significant digits; scientific counts decimals.
  const roundingExponent = format === 'fixed' ? -precision
    : exponent - precision + (format === 'general' ? 1 : 0);
  const roundingBound = physicalTime === 0 ? 0 : 0.5 * 10 ** roundingExponent;
  const binaryReadBound = 8 * Number.EPSILON * Math.abs(physicalTime);
  const maximumDifference = roundingBound + binaryReadBound;
  const candidates = fs.readdirSync(processorDirectory, {withFileTypes: true})
    .filter(entry => entry.isDirectory() && /^\d+(?:\.\d*)?(?:[eE][+-]?\d+)?$/.test(entry.name))
    .map(entry => ({directoryName: entry.name, observedTime: Number(entry.name)}))
    .filter(entry => Number.isFinite(entry.observedTime)
      && Math.abs(entry.observedTime - physicalTime) <= maximumDifference);
  if (candidates.length !== 1) {
    throw Error(`Expected one written time in ${processorDirectory} for ${physicalTime}`
      + ` (${format}, precision ${precision}); found ${candidates.length}`);
  }
  const selected = candidates[0];
  return {
    ...selected,
    path: path.join(processorDirectory, selected.directoryName),
    physicalTime,
    precision,
    format,
    difference: selected.observedTime - physicalTime,
    roundingBound,
    maximumDifference
  };
}
