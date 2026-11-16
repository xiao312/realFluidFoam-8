import {readFile,readdir,mkdir,copyFile} from 'node:fs/promises';
import {recipe,plan,dictionary,hash,patchTypes} from './recipe.mjs';
import {parsePoints,parseFaces,parseLabels,parseBoundary,faceArea} from '../coarse-wedge/ascii-mesh.mjs';

export const mode='reviewed-legacy-injector-v1';
const required=['boundary','points','faces','owner','neighbour'];
const optional=['pointZones','faceZones','cellZones'];
// Geometry serialization tolerances, not scientific solution-error tolerances.
const coordinateTolerance=1e-8;
function near(actual,expected,tolerance,name) {
  if(!Number.isFinite(actual)||Math.abs(actual-expected)>tolerance)
    throw Error(`${name}: measured ${actual}, expected ${expected}`);
}

export async function readMesh(directory) {
  const listing=await readdir(directory),raw={},files=[];
  for(const name of [...required,...optional.filter(n=>listing.includes(n))]) {
    raw[name]=await readFile(`${directory}/${name}`);
    files.push({name,sha256:hash(raw[name]),bytes:raw[name].length});
  }
  const points=parsePoints(raw.points),faces=parseFaces(raw.faces,points.length);
  const owner=parseLabels(raw.owner),neighbour=parseLabels(raw.neighbour),patches=parseBoundary(raw.boundary);
  const counts={points:points.length,faces:faces.length,internalFaces:neighbour.length,
    cells:Math.max(...owner,...neighbour)+1};
  if(counts.cells!==plan().expectedCells||owner.length!==faces.length||
     !Number.isInteger(counts.points)||counts.internalFaces<=0)
    throw Error('Tapered injector mesh differs from the qualified topology');
  for(const [x,y,z] of points) {
    if(x < -coordinateTolerance||x>.2+coordinateTolerance||y < -coordinateTolerance||
       Math.hypot(y,z)>.025+coordinateTolerance) throw Error('Point outside tapered injector recipe');
    if(Math.hypot(y,z)>coordinateTolerance)
      near(Math.abs(Math.atan2(z,y)*180/Math.PI),recipe.halfAngle_deg,1e-7,'Wedge angle');
  }
  const seen=new Set(owner);
  if(seen.size!==counts.cells) throw Error('Missing fluid-cell ownership');
  for(let i=0;i<neighbour.length;i++)
    if(neighbour[i]<=owner[i]||neighbour[i]>=counts.cells) throw Error('Invalid internal ownership');
  if(Object.keys(patches).sort().join()!==Object.keys(patchTypes).sort().join()) throw Error('Patch names differ');
  let next=neighbour.length,volume=0;const closure=[0,0,0];
  for(const [name,p] of Object.entries(patches)) {
    if(p.type!==patchTypes[name]||p.startFace!==next) throw Error(`Invalid patch type/range: ${name}`);
    Object.assign(p,{area:0,minX:Infinity,maxX:-Infinity,minRadius:Infinity,maxRadius:-Infinity});
    for(let i=p.startFace;i<p.startFace+p.faces;i++) {
      const vertices=faces[i].map(n=>points[n]),area=faceArea(vertices);
      p.area+=Math.hypot(...area);
      area.forEach((v,k)=>closure[k]+=v);
      volume+=vertices[0].reduce((s,x,k)=>s+x*area[k],0)/3;
      for(const [x,y,z] of vertices) {
        const r=Math.hypot(y,z);p.minX=Math.min(p.minX,x);p.maxX=Math.max(p.maxX,x);
        p.minRadius=Math.min(p.minRadius,r);p.maxRadius=Math.max(p.maxRadius,r);
      }
      if(['loxinlet','ch4inlet'].includes(name)&&area[0]>=0) throw Error('Inlet normal must point upstream');
    }
    if(!p.faces)p.minX=p.maxX=p.minRadius=p.maxRadius=null;
    next+=p.faces;
  }
  if(next!==faces.length||Math.hypot(...closure)>1e-10) throw Error('External surface is not closed');
  const factor=Math.sin(5*Math.PI/180)/2;
  const expectedVolume=factor*(.025**2*.19+.005*.0016**2+
    .005*(.0016**2+.0016*.0025+.0025**2)/3+
    .01*(.005**2-.0028**2)+.01*(.025**2-.0065**2));
  near(volume,expectedVolume,expectedVolume*1e-8,'Fluid volume');
  for(const [name,inner,outer] of [['loxinlet',0,.0016],['ch4inlet',.0028,.005]]) {
    const p=patches[name],full=Math.PI*(outer**2-inner**2);
    near(p.minRadius,inner,coordinateTolerance,`${name} inner radius`);
    near(p.maxRadius,outer,coordinateTolerance,`${name} outer radius`);
    near(p.minX,0,coordinateTolerance,`${name} plane`);
    near(p.maxX,0,coordinateTolerance,`${name} plane`);
    near(p.area,factor*(outer**2-inner**2),p.area*1e-8,`${name} area`);
    Object.assign(p,{fullAnnulusArea:full,wedgeAreaFraction:p.area/full});
  }
  const exits={oxygen:{area:0,faces:0},methane:{area:0,faces:0}};
  for(let i=0;i<neighbour.length;i++) {
    const vertices=faces[i].map(n=>points[n]);
    if(!vertices.every(p=>Math.abs(p[0]-.01)<=coordinateTolerance))continue;
    const radii=vertices.map(p=>Math.hypot(p[1],p[2])),lo=Math.min(...radii),hi=Math.max(...radii);
    const key=hi<=.0025+coordinateTolerance?'oxygen':lo>=.0028-coordinateTolerance&&hi<=.005+coordinateTolerance?'methane':null;
    if(key){exits[key].area+=Math.hypot(...faceArea(vertices));exits[key].faces++;}
  }
  near(exits.oxygen.area,factor*.0025**2,factor*.0025**2*1e-8,'Oxygen exit area');
  near(exits.methane.area,factor*(.005**2-.0028**2),factor*(.005**2-.0028**2)*1e-8,'Methane exit area');
  const referenceBytes=await readFile(new URL('./reference-boundary.json',import.meta.url));
  const reference=JSON.parse(referenceBytes),dist=(p,a,b)=>{
    const dx=b[0]-a[0],dy=b[1]-a[1],den=dx*dx+dy*dy;
    const t=den?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)):0;
    return Math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy);
  };
  const distanceTo=(p,edges)=>Math.min(...edges.map(e=>dist(p,e[0],e.at(-1))));
  const geometryErrors={};
  for(const row of reference){
    const patch=patches[row.patch],edges=[];
    for(let i=patch.startFace;i<patch.startFace+patch.faces;i++){
      const vertices=faces[i].map(j=>[points[j][0],Math.hypot(points[j][1],points[j][2])]);
      const unique=[...new Map(vertices.map(p=>[p.map(x=>Math.round(x/1e-10)).join(','),p])).values()];
      unique.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);edges.push(unique);
    }
    const a=Math.max(...edges.flat().map(p=>distanceTo(p,row.edges)));
    const b=Math.max(...row.edges.flat().map(p=>distanceTo(p,edges)));
    geometryErrors[row.patch]={generatedToReference_m:a,referenceToGenerated_m:b};
    if(Math.max(a,b)>coordinateTolerance)throw Error('Changed reviewed geometry '+row.patch+' '+JSON.stringify(geometryErrors[row.patch]));
  }
  return {schema:'g2-tapered-injector-measured-mesh/v1',mode,recipeSha256:plan().recipeSha256,
    counts,pointCount:counts.points,faceCount:counts.faces,cellCount:counts.cells,
    files,meshSha256:hash(JSON.stringify(files)),patches,exits,volume_m3:volume,
    geometryErrors,referenceBoundarySha256:hash(referenceBytes),surfaceClosure_m2:closure,diagnosticAxialOrigin_m:0,paperAxialOrigin_m:.01,
    upstreamPlane_m:0,upstreamDucts:true,axisymmetricBoundaryType:'empty',
    matchedFeatures:['3.2-to-5mm oxygen taper','0.3mm lip','5.6/10mm methane annulus','13mm casing and upstream outer fluid pocket'],
    omittedFeatures:recipe.limitations,paperGeometryQualified:false,
    interpretation:'Owner-reviewed legacy geometry; raw injector exit x=.01m' };
}

export async function evidence(root,logs=root,dictionaryPath='blockMeshDict') {
  const d=await readFile(`${root}/${dictionaryPath}`),r=await readFile(`${root}/mesh-recipe.json`);
  if(hash(d)!==hash(dictionary())||JSON.parse(r).recipeSha256!==plan().recipeSha256) throw Error('Recipe/dictionary identity differs');
  const receipts={};
  for(const name of ['log.blockMesh','log.checkMesh']) {
    const bytes=await readFile(`${logs}/${name}`),text=bytes.toString();
    if(!/\nEnd\s*(\n|$)/.test(text)||/FOAM FATAL|Segmentation fault/.test(text)||
       (name==='log.checkMesh'&&!text.includes('Mesh OK.')))throw Error(`Incomplete or failed ${name}`);
    receipts[name]={sha256:hash(bytes),bytes:bytes.length};
  }
  return {dictionarySha256:hash(d),recipeReceiptSha256:hash(r),logs:receipts};
}
export async function inspectInjectorMesh(root) {
  const bytes=await readFile(`${root}/manifest.json`),m=JSON.parse(bytes);
  if(m.schema!=='g2-reviewed-injector-qualified-asset/v1'||m.mode!==mode)throw Error('Not a qualified tapered-injector asset');
  const actual=await readMesh(`${root}/polyMesh`),e=await evidence(root);
  if(m.meshSha256!==actual.meshSha256||JSON.stringify(m.files)!==JSON.stringify(actual.files)||
     JSON.stringify(m.evidence)!==JSON.stringify(e))throw Error('Measured mesh/evidence changed after qualification');
  return {...actual,evidence:e,manifestSha256:hash(bytes)};
}
export async function copyInjectorMesh(root,out) {
  const m=await inspectInjectorMesh(root);await mkdir(`${out}/constant/polyMesh`);
  for(const file of m.files)await copyFile(`${root}/polyMesh/${file.name}`,`${out}/constant/polyMesh/${file.name}`);
}
