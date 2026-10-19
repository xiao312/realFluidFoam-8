"""Create isolated cross-solver phi110 cases from the versioned ideal baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def header(name, kind='dictionary'):
    return f'FoamFile {{version 2.0; format ascii; class {kind}; object {name};}}\n'


def prepare(action, family, case):
    if case.exists():
        raise ValueError('Refusing existing case: ' + str(case))
    plan = {'family': family, 'phi': 1.1, 'cells': 8000, 'pressure_Pa': 10132500,
            'max_delta_t_s': 5e-8, 'end_time_s': 2e-4,
            'gamma': 1.3867396282842988, 'gamma_source': 'qualified ideal donor job 124878193',
            'output': str(case.resolve()), 'scientific_status': 'unqualified comparison'}
    print(json.dumps(plan, indent=2))
    if action == 'plan':
        return
    subprocess.run([sys.executable, '-B', str(HERE.parent/'ideal-baseline/prepare.py'),
                    'apply', 'phi110', str(case), 'full'], check=True)
    def write(name, text):
        (case/name).write_text(text, encoding='utf8')
    p = case/'0/p'
    write('0/p', p.read_text().replace('gamma 1;', f'gamma {plan["gamma"]};'))
    # Remove custom runtime diagnostics; use stock read-only sampling in each ABI.
    for name in ['flameSpeedProperties', 'frontTrackingProperties']:
        p = case/'constant'/name
        if p.exists():
            p.unlink()
    if family == 'stock':
        p = case/'constant/thermophysicalProperties'
        write('constant/thermophysicalProperties', p.read_text().replace(
            'idKineticMixture', 'multiComponentMixture').replace('sutherlandKinetic', 'sutherland'))
        p = case/'constant/chemistryProperties'
        write('constant/chemistryProperties', p.read_text().replace('idKineticStandard', 'standard'))
        write('constant/thermophysicalTransport', header('thermophysicalTransport')+
              'simulationType laminar;\nlaminar { model Fourier; }\n')
        solver = 'reactingFoam'
    elif family == 'deep':
        write('constant/thermophysicalProperties', header('thermophysicalProperties'))
        write('constant/turbulenceProperties', header('turbulenceProperties')+'simulationType laminar;\n')
        write('constant/g', header('g', 'uniformDimensionedVectorField')+
              'dimensions [0 1 -2 0 0 0 0]; value (0 0 0);\n')
        # dfLowMachFoam constructs a spray cloud even for gas-only cases.
        # Match the pinned upstream gas-flame tutorial's inactive cloud.
        write('constant/sprayCloudProperties', header('sprayCloudProperties')+
              'solution {active false; coupled false; transient no; cellValueSourceCorrection off;}\n')
        write('constant/CanteraTorchProperties', header('CanteraTorchProperties')+'''
chemistry on;
CanteraMechanismFile "constant/author-gri30.yaml";
transportModel "Mix";
odeCoeffs {relTol 1e-9; absTol 1e-15;}
inertSpecie "N2";
splittingStrategy off;
TorchSettings {torch off; GPU off; log off;}
loadbalancing {active true; log false; algorithm allAverage;}
''')
        solver = 'dfLowMachFoam'
        p = case/'system/fvSolution'
        write('system/fvSolution', p.read_text().replace('"Yi.*"', '"(Yi.*|Y.*|ha.*|hs.*)"'))
    else:
        raise ValueError('Unknown family')
    p = case/'system/controlDict'
    text = re.sub(r'application\s+[^;]+;', 'application '+solver+';', p.read_text())
    text += '''
functions
{
    profiles
    {
        type sets; libs ("libsampling.so");
        writeControl timeStep; writeInterval 10;
        interpolationScheme cellPoint; setFormat raw;
        fields (T U rho OH p);
        sets
        (
            axisLine {type uniform; axis x; start (0.00000025 0.000005 0.000005);
                      end (0.00399975 0.000005 0.000005); nPoints 8000;}
        );
    }
}
'''
    if family == 'stock':
        text = text.replace('type uniform;', 'type lineUniform;')
    write('system/controlDict', text)
    plan['input_sha256'] = {str(p.relative_to(case)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for sub in ['0', 'constant', 'system']
                            for p in sorted((case/sub).rglob('*')) if p.is_file()}
    write('comparison-inputs.json', json.dumps(plan, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply'])
    parser.add_argument('family', choices=['stock', 'deep'])
    parser.add_argument('case', type=Path)
    args = parser.parse_args()
    prepare(args.action, args.family, args.case)

