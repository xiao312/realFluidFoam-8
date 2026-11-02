import {scanSolverLog} from './reader.mjs';
const [path,...extra]=process.argv.slice(2);if(!path||extra.length)throw Error('Use inspect.mjs RETAINED_LOG');
const {identity}=await scanSolverLog(path);const {sourceLineMappings,markerSourceLines,...small}=identity;
console.log(JSON.stringify(small,null,2));
