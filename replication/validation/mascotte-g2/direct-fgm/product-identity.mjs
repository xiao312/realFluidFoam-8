import {createHash} from 'node:crypto';

// Full-build receipts record bytes. Derived-build receipts instead identify an
// inherited library by its exact SHA256 and resolved parent path. Both bind the
// actual bytes; absent size must never be compared to JavaScript undefined.
export function verifyProductBytes(product, raw) {
  const inherited = product.reused === true && typeof product.resolved === 'string'
    && product.resolved.startsWith('/workspace/build/');
  const sized = Number.isSafeInteger(product.bytes) && product.bytes > 0;
  if ((!sized && !inherited) || (product.bytes !== undefined && !sized))
    throw Error(`Missing valid product size or inherited identity: ${product.file}`);
  if (!/^[a-f0-9]{64}$/.test(product.sha256 ?? '') ||
      createHash('sha256').update(raw).digest('hex') !== product.sha256 ||
      (sized && raw.length !== product.bytes))
    throw Error(`Full-library product identity mismatch: ${product.file}`);
  return {bytes:raw.length, sha256:product.sha256, inherited};
}
