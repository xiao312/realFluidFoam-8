// Operator names follow reactingFoamSolveZ and OF8 linearViscousStress/Fourier.
// Keep the explicit stress term even when a simple verification has zero grad U.
export function solverSchemes(defaultDivergence = 'none') {
  if (!['none', 'Gauss linear'].includes(defaultDivergence)) throw new Error('Unsupported divergence default');
  return `ddtSchemes { default Euler; }
gradSchemes { default Gauss linear; }
divSchemes {
 default ${defaultDivergence};
 div(phi,U) Gauss upwind;
 div(phi,Yi_h) Gauss upwind;
 div(phi,Z) Gauss upwind; div(phi,c) Gauss upwind;
 div(phi,h) Gauss upwind; div(phi,Ha) Gauss upwind; div(phi,e) Gauss upwind;
 div(phi,K) Gauss upwind;
 div(phiv,p) Gauss linear; div(phid,p) Gauss upwind;
 div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
fluxRequired { default no; p; }
`;
}
