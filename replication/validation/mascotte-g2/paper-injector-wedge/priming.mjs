import {taperLength} from './recipe.mjs';

// Fresh-time-zero composition in the two upstream fluid passages. Pressure and
// velocity remain owned by the case; full SRK Ha initialization follows setFields.
export function injectorRegions(streams,names,realFluid) {
  return [['loxinlet',-.000001,.0026],['ch4inlet',.0026,.0051]].map(([name,low,high])=>{
    const state=streams[name];
    const fields=[['T',state.temperature],['Z',state.z],['c',state.c],
      ...(!realFluid?[['Ha',state.thermo.enthalpy]]:[]),...names.map((n,i)=>[n,state.y[i]])];
    if(fields.some(([,value])=>!Number.isFinite(value)))throw Error('Invalid pure-stream priming state');
    return `boxToCell { box (${-taperLength-1e-9} ${low} -0.01) (0 ${high} 0.01);
 fieldValues (${fields.map(([n,v])=>`volScalarFieldValue "${n}" ${v}`).join('\n')}); }`;
  }).join('\n');
}
