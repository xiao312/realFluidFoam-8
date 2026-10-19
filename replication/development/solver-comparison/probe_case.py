"""Make a short cell array containing independent chemistry test states."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from prepare import header

HERE = Path(__file__).resolve().parent


def prepare(family, tolerance, states_path, output):
    if output.exists():
        raise ValueError('Refusing existing '+str(output))
    states = json.loads(states_path.read_text())['states']
    subprocess.run([sys.executable, '-B', str(HERE.parent/'ideal-baseline/prepare.py'),
                    'apply', 'phi110', str(output), 'smoke'], check=True)
    n = len(states)
    p = output/'system/blockMeshDict'
    p.write_text(p.read_text().replace('(8000 1 1)', f'({n} 1 1)'))
    for name in list(states[0]['Y'])+['T', 'p']:
        values = [s['Y'][name] if name not in ['T', 'p'] else s[name] for s in states]
        dimensions = '0 0 0 1 0 0 0' if name == 'T' else ('1 -1 -2 0 0 0 0' if name == 'p' else '0 0 0 0 0 0 0')
        text = header(name, 'volScalarField')+f'dimensions [{dimensions}];\n'
        text += f'internalField nonuniform List<scalar>\n{n}\n(\n'
        text += '\n'.join(format(v, '.17g') for v in values)+'\n);\n'
        text += 'boundaryField {left {type zeroGradient;} right {type zeroGradient;} sides {type empty;}}\n'
        (output/'0'/name).write_text(text)
    if family == 'stock':
        p = output/'constant/thermophysicalProperties'
        p.write_text(p.read_text().replace('idKineticMixture', 'multiComponentMixture').replace('sutherlandKinetic','sutherland'))
        p = output/'constant/chemistryProperties'
        p.write_text(p.read_text().replace('idKineticStandard','standard'))
    if tolerance == 'tight':
        p = output/'constant/chemistryProperties'
        p.write_text(p.read_text().replace('absTol 1e-8', 'absTol 1e-12').replace('relTol 1e-6', 'relTol 1e-8'))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('family', choices=['stock','native']); p.add_argument('tolerance',choices=['base','tight'])
    p.add_argument('states',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();prepare(a.family,a.tolerance,a.states,a.output)
