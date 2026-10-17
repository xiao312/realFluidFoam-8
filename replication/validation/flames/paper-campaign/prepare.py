"""Plan or create versioned paper-condition cases without altering the solver."""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLAMES = HERE.parent


def write(path, text):
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def run(script, *args):
    subprocess.run([sys.executable, '-B', str(script), *map(str, args)], check=True)


def configuration(key):
    if not re.fullmatch(r'[a-z0-9-]+', key):
        raise ValueError('Invalid case key')
    cfg = json.loads((HERE / 'cases' / (key + '.json')).read_text())
    family = cfg['family']
    if family == 'counterflow':
        if set(cfg) != {'family', 'condition'} or cfg['condition'] not in ('oxy-200', 'air-100'):
            raise ValueError('Invalid counterflow configuration')
    elif family == 'premixed':
        if set(cfg) != {'family', 'phi', 'cells', 'length_m', 'kernel_width_m', 'delta_t_s'}:
            raise ValueError('Invalid premixed schema')
        if not .9 <= cfg['phi'] <= 1.4 or type(cfg['cells']) is not int or cfg['cells'] % 4:
            raise ValueError('Invalid phi or cell count')
        if not 0 < cfg['kernel_width_m'] < cfg['length_m'] or cfg['cells'] < 4:
            raise ValueError('Invalid domain/kernel')
        if not math.isfinite(cfg['delta_t_s']) or not 0 < cfg['delta_t_s'] <= 1e-8:
            raise ValueError('Invalid timestep')
    else:
        raise ValueError('Unsupported family')
    return cfg


def patch_boundary(path, patch, body):
    text = path.read_text()
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    text, count = re.subn(r'\b' + patch + r'\s*\{[^{}]*\}', patch + ' { ' + body + ' }', text)
    if count != 1:
        raise ValueError('Ambiguous patch: ' + str(path))
    write(path, text)


def counterflow(output, cfg, mode):
    run(FLAMES / 'author-counterflow/prepare.py', 'apply', output, mode)
    air = cfg['condition'] == 'air-100'
    pressure = (100 if air else 200) * 101325
    length = .02 if air else .005
    for phase in ('one-step', 'gri30'):
        case = output / phase
        p = case / '0/p'
        pressure_text = re.sub(r'/\*.*?\*/|//[^\n]*', '', p.read_text(), flags=re.S)
        pressure_text, count = re.subn(r'\binternalField\s+uniform\s+[^;]+;',
                                      f'internalField uniform {pressure};', pressure_text)
        if count != 1:
            raise ValueError('Ambiguous pressure initial field')
        write(p, pressure_text)
        if not air:
            mesh = case / 'system/blockMeshDict'
            write(mesh, mesh.read_text().replace('halfZone 4.0;', 'halfZone 1.0;')
                  .replace('yhalfDomain 10;', 'yhalfDomain 2.5;').replace('r1 20;', 'r1 5;'))
        else:
            thermo_name = 'thermo.inputData' if phase == 'one-step' else 'thermo.inputData_GRI'
            thermo = (case / 'constant' / thermo_name).read_text()
            weights = {s: float(re.search(r'(?m)^' + s + r'\s*\{\s*specie\s*\{\s*molWeight\s+([\d.]+)', thermo).group(1)) for s in ('O2', 'N2')}
            oxygen = .21 * weights['O2'] / (.21 * weights['O2'] + .79 * weights['N2'])
            for species, value in [('O2', oxygen), ('N2', 1-oxygen), ('CO2', 0)]:
                patch_boundary(case / '0' / species, 'oxidizer', f'type fixedValue; value uniform {value:.16g};')
            patch_boundary(case / '0/T', 'oxidizer', 'type fixedValue; value uniform 300;')
        # These two patches are finalized from this phase's actual library densities.
        for patch in ('fuel', 'oxidizer'):
            patch_boundary(case / '0/U', patch, 'type fixedValue; value uniform (0 0 0);')
        write(case / 'pilot.json', json.dumps(dict(case=cfg['condition'], pressure_Pa=pressure,
              length_m=length, velocity_constraint='mass' if air else 'momentum',
              velocities_finalized=False), indent=2) + '\n')
        meta = json.loads((case / 'author-case.json').read_text())
        meta.update(condition=cfg['condition'], adaptation='paper operating condition on original tutorial mesh')
        write(case / 'author-case.json', json.dumps(meta, indent=2) + '\n')


def premixed(output, cfg, mode):
    output.mkdir(parents=True, exist_ok=False)
    dt = cfg['delta_t_s']
    campaign = dict(case='premixed', axial_cells=cfg['cells'], phi=cfg['phi'],
        length_m=cfg['length_m'], kernel_width_m=cfg['kernel_width_m'], delta_t_s=dt,
        end_time_s=10*dt if mode == 'smoke' else .001,
        write_interval_steps=10 if mode == 'smoke' else round(1e-5/dt), ranks=4, wall_minutes=480)
    config_path = output / 'generation.json'
    write(config_path, json.dumps(campaign, indent=2))
    run(FLAMES / 'campaign.py', 'apply', config_path, FLAMES.parent / 'inputs', output / 'premixed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply'])
    parser.add_argument('key')
    parser.add_argument('output', type=Path)
    parser.add_argument('mode', choices=['smoke', 'full'])
    args = parser.parse_args()
    cfg = configuration(args.key)
    if args.output.exists():
        raise ValueError('Refusing existing output')
    ranks = 8 if cfg['family'] == 'counterflow' else 4
    minutes = 30 if args.mode == 'smoke' else (720 if ranks == 8 else 480)
    receipt = dict(key=args.key, mode=args.mode, configuration=cfg, ranks=ranks,
                   wall_minutes=minutes, reserved_core_hours=ranks*minutes/60,
                   status='planned; no scientific acceptance')
    print(json.dumps(receipt, indent=2))
    if args.action == 'plan':
        return
    if cfg['family'] == 'counterflow':
        counterflow(args.output, cfg, args.mode)
    else:
        premixed(args.output, cfg, args.mode)
    receipt['input_hashes'] = {p.relative_to(args.output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted(args.output.rglob('*')) if p.is_file()}
    write(args.output / 'paper-case.json', json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
