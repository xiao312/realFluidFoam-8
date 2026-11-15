"""Read-only scalar reconstruction; no scheduler, field writes or CFD restarts."""
from pathlib import Path
import argparse,csv,json,re,math,tarfile
import numpy as np
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--state-root',type=Path,required=True)
args=parser.parse_args();r=args.state_root.resolve();o=r/'overnight-20261115';RR=8314.4700665054497
def ideal(T):
 h=cp=hf=0.
 for name,y in Y.items():
  sp=species[name];a=sp['low'if T<sp['mid']else'high'];a0=sp['low'];fac=y*RR/sp['W'];h+=fac*(sum(a[k]*T**(k+1)/(k+1)for k in range(5))+a[5]);cp+=fac*sum(a[k]*T**k for k in range(5));hf+=fac*(sum(a0[k]*298.15**(k+1)/(k+1)for k in range(5))+a0[5])
 return h,cp,hf

def state(rho,T):
 h0,cp,hf=ideal(T);a=c['coef1']-c['coef2']*math.sqrt(T)+c['coef3']*T;da=-c['coef2']/(2*math.sqrt(T))+c['coef3'];d2a=c['coef2']/(4*T**1.5);v=W/rho;pressure=RR*T/(v-b)-a/(v*(v+b));r=RR/W;E=h0-r*T+(T*da-a)/(b*W)*math.log1p(b/v);Cv=cp-r+T*d2a/(b*W)*math.log1p(b/v);return dict(p=pressure,e=E,Cv=Cv,hs=E+pressure/rho-hf,hf=hf)

def setup(q,text):
 global species,Y,W,b,c
 species={};Y=q['massFractions'];W=1/sum(Y[n]/float(re.search(r'molWeight\s+([^;]+);',block(text,n))[1])for n in Y)
 for n in Y:
  body=block(text,n);scalar=lambda key:float(re.search(r'\b'+key+r'\s+([^;]+);',body)[1]);coeff=lambda key:list(map(float,re.search(r'\b'+key+r'\s+\(([^)]+)\)',body)[1].split()))
  species[n]=dict(W=scalar('molWeight'),mid=scalar('Tcommon'),low=coeff('lowCpCoeffs'),high=coeff('highCpCoeffs'),Tc=scalar('Tc'),Pc=scalar('Pc')*1e6,omega=scalar('omega'))
 X={n:Y[n]*W/sp['W']for n,sp in species.items()};b=0;c=dict(coef1=0.,coef2=0.,coef3=0.)
 for n,sp in species.items():
  b+=X[n]*.08664*RR*sp['Tc']/sp['Pc']
  for m,sj in species.items():
   si=.48508+1.5517*sp['omega']-.15613*sp['omega']**2;ss=.48508+1.5517*sj['omega']-.15613*sj['omega']**2
   a=math.sqrt((.42747*(RR*sp['Tc'])**2/sp['Pc'])*(.42747*(RR*sj['Tc'])**2/sj['Pc']))*X[n]*X[m]
   c['coef1']+=a*(1+si)*(1+ss);c['coef2']+=a*((1+ss)*si/math.sqrt(sp['Tc'])+(1+si)*ss/math.sqrt(sj['Tc']));c['coef3']+=a*si*ss/math.sqrt(sp['Tc']*sj['Tc'])
def block(text,n):
 m=re.search(r'(?m)^\s*"'+re.escape(n)+r'"\s*\{',text);assert m,n;i=m.end();start=i;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i-1]
def roots(P,T):
 a=c['coef1']-c['coef2']*math.sqrt(T)+c['coef3']*T;A=a*P/(RR*T)**2;B=b*P/(RR*T);out=[]
 for z in np.roots([1,-1,A-B-B*B,-A*B]):
  if abs(z.imag)>1e-9 or z.real<=B:continue
  z=float(z.real);rho=P*W/(z*RR*T);s=state(rho,T);out.append(dict(Z=z,rho=rho,Hs=s['hs'],stable=3*z*z-2*z+A-B-B*B>0,gibbs=z-1-math.log(z-B)-(A/B)*math.log1p(B/z)))
 return sorted(out,key=lambda x:x['Z'])
q=json.loads((r/'cavalieri-fixedtime-failed-point.json').read_text(encoding='utf8'));text=(r/'cavalieri-failed-thermophysicalProperties').read_text(encoding='utf8');setup(q,text)
actual={k:float(v)for k,v in next(csv.DictReader((r/'s05-queries/scan/srk-coefficients.csv').open())).items()};relative={k:abs(v-actual[k])/max(abs(actual[k]),1e-30)for k,v in dict(W_kg_kmol=W,b_m3_kmol=b,**c).items()};assert max(relative.values())<1e-12,relative
checks=[]
for row in csv.DictReader((r/'s05-queries/scan/cold-properties.csv').open()):
 s=state(float(row['rho_kg_m3']),float(row['T_K']));checks.append(dict(p=abs(s['p']-float(row['p_Pa']))/float(row['p_Pa']),hs=abs(s['hs']-float(row['Hs_J_kg'])),cv=abs(s['Cv']-float(row['Cv_J_kg_K']))))
assert max(x['p']for x in checks)<1e-10 and max(x['hs']for x in checks)<1e-5
reports=[]
for label in ['s24','s25','s26']:
 q=json.loads((o/(label+'-failed-point.json')).read_text(encoding='utf8'))
 with tarfile.open(o/(label+'-failed-rank-fields.tar.gz'))as tar:
  member=next(m for m in tar.getmembers()if m.name.endswith('/constant/thermophysicalProperties'));text=tar.extractfile(member).read().decode()
 setup(q,text);rho=q['rho_kg_m3'];P=q['p_Pa'];T=q['T_K'];target=q['Ha_J_kg'];at=roots(P,T);lo,hi=60.,6000.
 f=lambda t:state(rho,t)['e']+state(rho,t)['p']/rho-target
 assert f(lo)*f(hi)<0
 for _ in range(100):
  mid=(lo+hi)/2
  if f(mid)>0:hi=mid
  else:lo=mid
  if hi-lo<1e-12:break
 t=(lo+hi)/2;s=state(rho,t);rr=roots(s['p'],t);stable=[x for x in rr if x['stable']];z=s['p']*W/(rho*RR*t)
 v=W/rho;a=c['coef1']-c['coef2']*math.sqrt(t)+c['coef3']*t;slope=-W/rho**2*(-RR*t/(v-b)**2+a*(2*v+b)/(v*v*(v+b)**2))
 nearest=min(rr,key=lambda x:abs(x['Z']-z));rep=dict(label=label,job=q['job'],time_s=q['time_s'],stored=dict(T=T,p=P,rho=rho,Hs=q['storedHs_J_kg'],Ha=target),fixedPTroots=at,largestRootHsMismatch_J_kg=at[-1]['Hs']-q['storedHs_J_kg'],loggedHsMismatch_J_kg=q['logged']['evaluatedH_J_kg']-q['logged']['storedH_J_kg'],fixedRhoHa=dict(T=t,p=s['p'],pressureChange_Pa=s['p']-P,HaResidual_J_kg=f(t),isothermalSlope=slope,largestRootDensityRelativeError=abs(rr[-1]['rho']-rho)/rho,minGibbsStableRoot=bool(stable)and abs(nearest['gibbs']-min(x['gibbs']for x in stable))<1e-10,roots=rr),scientificAcceptance=False)
 assert abs(rep['largestRootHsMismatch_J_kg']-rep['loggedHsMismatch_J_kg'])<1e-4
 reports.append(rep)
report=dict(reference85rows=dict(rows=len(checks),coefficientRelative=relative,maxPressureRelative=max(x['p']for x in checks),maxHsError_J_kg=max(x['hs']for x in checks),maxCvError_J_kg_K=max(x['cv']for x in checks)),failedStates=reports,scope='Independent scalar postprocessing of retained actual53Y/dictionary/rho/Ha; no state write, phase flash, changed root selection or CFD qualification. NASA below200K remains unqualified.',scientificAcceptance=False)
(o/'failed-mixtures-audit-0500.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print(json.dumps(report,indent=2))
