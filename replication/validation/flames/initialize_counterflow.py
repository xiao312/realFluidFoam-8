"""Initialize a declared cold mixing layer with localized ignition, without fitting paper curves."""
import json,math,re,sys
from pathlib import Path
case=Path(sys.argv[1]).resolve(strict=True)
cfg=json.loads((case/'campaign.json').read_text())['initialization']
meta=json.loads((case/'pilot.json').read_text())
if not meta.get('velocities_finalized'):raise ValueError('Finalize library-derived inlet velocities first')
count=meta['cells'];length=meta['length_m'];oxygen=meta['oxidizer_mass_fraction_O2']
text=(case/'0/C').read_text();m=re.search(r'internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
if not m or int(m.group(1))!=count:raise ValueError('Missing or invalid OpenFOAM-written cell centres')
coords=[tuple(map(float,s.split())) for s in re.findall(r'\(([^()]+)\)',m.group(2))]
if len(coords)!=count or any(len(c)!=3 for c in coords):raise ValueError('Cell-centre size mismatch')
# Stoichiometric oxygen-to-methane mass ratio is derived from the pinned species weights.
thermo=(case/'constant/thermo.inputData_GRI').read_text();weights={}
for name in ['CH4','O2']:
 weights[name]=float(re.search(r'(?m)^'+name+r'\s*\{\s*specie\s*\{\s*molWeight\s+([\d.]+)',thermo).group(1))
ratio=2*weights['O2']/weights['CH4'];zst=oxygen/(ratio+oxygen)
mixwidth=cfg['mixing_width_fraction']*length;centre=.5*length+mixwidth*math.atanh(1-2*zst)
ignwidth=cfg['ignition_width_fraction']*length;peak=cfg['ignition_temperature_K']
air=meta['case']=='air-100';oxidizerT=300 if air else 1000;inert='N2' if air else 'CO2'
values={'T':[],'CH4':[],'O2':[],inert:[],'U':[]};uf=meta['inlet_speed_m_s']['fuel'];uo=meta['inlet_speed_m_s']['oxidizer'];gradient=(uf+uo)/length
for x,y,z in coords:
 fraction=.5*(1-math.tanh((z-.5*length)/mixwidth));base=300*fraction+oxidizerT*(1-fraction)
 values['T'].append(base+(peak-base)*math.exp(-((z-centre)/ignwidth)**2))
 values['CH4'].append(fraction);values['O2'].append((1-fraction)*oxygen);values[inert].append((1-fraction)*(1-oxygen))
 values['U'].append((.5*gradient*x,.5*gradient*y,uf-gradient*z) if cfg['strain_flow'] else (0,0,0))
for name,rows in values.items():
 path=case/'0'/name;text=path.read_text();vector=name=='U'
 body='\n'.join('('+ ' '.join(f'{v:.16g}' for v in row)+')' if vector else f'{row:.16g}' for row in rows)
 replace=f'internalField nonuniform List<{"vector" if vector else "scalar"}>\n{count}\n(\n{body}\n);'
 text,n=re.subn(r'internalField\s+uniform\s+[^;]+;',replace,text)
 if n!=1:raise ValueError('Expected fresh uniform field: '+name)
 with path.open('w',newline='\n') as stream:stream.write(text)
sums=[a+b+c for a,b,c in zip(values['CH4'],values['O2'],values[inert])]
record={'initialization':cfg,'stoichiometric_mixture_fraction':zst,'ignition_centre_m':centre,
        'T_min_K':min(values['T']),'T_max_K':max(values['T']),'mass_fraction_sum_max_error':max(abs(v-1) for v in sums),
        'qualification':'Reconstructed ignition state; not a simulation result or fitted paper profile.'}
(case/'initialization.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
