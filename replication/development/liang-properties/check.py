"""Check implementation invariants; reference agreement is a separate result."""
import csv
import json
import math
import sys
from pathlib import Path


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def check(root):
    oxygen=rows(root/'oxygen.csv'); critical=rows(root/'critical.csv')
    assert len(oxygen)==901 and len(critical)==282
    for i,r in enumerate(oxygen):
        assert float(r['T_K'])==100+i and float(r['p_Pa'])==10132500
        assert int(r['caloric_extrapolated'])==(i<100)
        for key in ['rho_kg_m3','kappa_W_m_K','kappa_mass_mapping_W_m_K','cp0_R']:
            assert math.isfinite(float(r[key])) and float(r[key])>0
    residual=max(abs(float(r[k])) for r in critical for k in ['dp_normalized','d2p_normalized'])
    assert residual<1e-10
    pure=rows(root/'pure-critical.csv')
    expected={'H2':(33.18,1.3),'O2':(154.58,5.043),'N2':(126.19,3.398),'CH4':(190.6,4.61)}
    for r in pure:
        t,p=expected[r['fuel']]
        assert abs(float(r['Tc_K'])/t-1)<1e-4
        assert abs(float(r['Pc_atm'])*101325/(p*1e6)-1)<1e-4
    result={'finite_oxygen_states':len(oxygen),'critical_states':len(critical),
            'max_normalized_derivative_residual':residual,'extrapolated_caloric_states':100,
            'scientific_acceptance':False}
    (root/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':check(Path(sys.argv[1]))
