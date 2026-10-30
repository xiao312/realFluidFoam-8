import test from 'node:test';
import assert from 'node:assert/strict';
import { solverSchemes } from './schemes.mjs';

// Required interface from UEqn, EEqn, pEqn, multivariate scalar transport and
// OF8 linearViscousStress::divDevTau, not a guessed default fallback.
const operators = ['div(phi,U)', 'div(phi,Yi_h)', 'div(phi,Z)', 'div(phi,c)',
  'div(phi,h)', 'div(phi,Ha)', 'div(phi,e)', 'div(phi,K)', 'div(phiv,p)', 'div(phid,p)',
  'div(((rho*nuEff)*dev2(T(grad(U)))))'];
for (const fallback of ['none', 'Gauss linear']) {
  test(`Selected solver operators are explicit with default ${fallback}`, () => {
    const dictionary = solverSchemes(fallback);
    for (const key of operators) assert.ok(dictionary.includes(`${key} Gauss `), `Missing ${key}`);
    assert.ok(dictionary.includes(`default ${fallback};`));
    assert.ok(dictionary.includes('laplacianSchemes { default Gauss linear corrected; }'));
    assert.ok(dictionary.includes('gradSchemes { default Gauss linear; }'));
  });
}
