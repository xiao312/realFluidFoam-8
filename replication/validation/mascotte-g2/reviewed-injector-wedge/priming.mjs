export function reviewedRegions(streams,names,realFluid){
 return [['loxinlet',0,.0026],['ch4inlet',.0026,.0051]].map(([patch,lo,hi])=>{
  const s=streams[patch],fields=[['T',s.temperature],['Z',s.z],['c',s.c],
   ...(!realFluid?[['Ha',s.thermo.enthalpy]]:[]),...names.map((n,i)=>[n,s.y[i]])];
  if(fields.some(([,v])=>!Number.isFinite(v)))throw Error('Nonfinite reviewed duct state');
  return `boxToCell { box (-1e-9 ${lo} -.01) (.01 ${hi} .01); fieldValues (${fields.map(([n,v])=>`volScalarFieldValue "${n}" ${v}`).join('\n')}); }`;
 }).join('\n');
}
