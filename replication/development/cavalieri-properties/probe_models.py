"""Probe the Cantera 3.2 build for the models needed by Cavalieri et al. (2025) Fig. 1.

Fig. 1 needs, for pure O2 and pure CH4 at 56 bar and 100-400 K:
  * an SRK equation of state for density and isobaric specific heat,
  * the Chung et al. (1988) method for dynamic viscosity and thermal conductivity.

This probe does not produce figure data.  It reports which model names this
Cantera installation accepts, and what each accepted variant returns at a few
state points, so the figure driver can be written against the real API.  Every
failure is printed with its full exception text rather than swallowed.
"""
import json
import os
import sys
import traceback

OUT = {}


def show(title, fn):
    print('\n=== %s ===' % title)
    try:
        value = fn()
    except BaseException as exc:                       # noqa: BLE001 - report everything
        print('FAILED: %s: %s' % (type(exc).__name__, exc))
        traceback.print_exc()
        return None
    print('OK')
    return value


def main():
    import cantera as ct
    print('cantera', ct.__version__)
    print('module ', ct.__file__)
    print('python ', sys.version.replace('\n', ' '))
    print('data   ', ct.data_path())
    OUT['version'] = ct.__version__

    gas = show('load gri30.yaml', lambda: ct.Solution('gri30.yaml'))
    if gas is None:
        return 1

    print('\nspecies with thermo:', [s for s in ('O2', 'CH4') if s in gas.species_names])
    for name in ('O2', 'CH4'):
        sp = gas.species(name)
        th = sp.thermo
        print('\n%s thermo=%s Tmin=%.1f Tmax=%.1f' % (name, type(th).__name__,
                                                      th.min_temp, th.max_temp))
        try:
            print('  coeffs', json.dumps([list(map(float, c)) for c in th.coeffs]))
        except BaseException as exc:                   # noqa: BLE001
            print('  coeffs unavailable: %s' % exc)
        print('  critical: Tc=%.4f pc=%.4f vc=%.6f omega=%.5f' % (
            sp.critical_temperature, sp.critical_pressure,
            sp.critical_volume, sp.acentric_factor))

    # ---- model discovery -------------------------------------------------
    names = [n for n in dir(ct) if 'edlich' in n or 'eng' in n or 'HighPressure' in n]
    print('\nct names of interest:', names)
    OUT['ct_names'] = names

    root = os.path.dirname(os.path.dirname(ct.__file__))
    hits = {}
    for rel in ('cantera/data', 'cantera', 'share/cantera'):
        d = os.path.join(root, rel)
        if not os.path.isdir(d):
            continue
        for base, _dirs, files in os.walk(d):
            for f in files:
                if not f.endswith(('.py', '.yaml', '.h', '.cpp')):
                    continue
                path = os.path.join(base, f)
                try:
                    text = open(path, encoding='utf-8', errors='replace').read()
                except OSError:
                    continue
                for key in ('RedlichKwong', 'PengRobinson', 'high-pressure',
                            'HighPressureGas', 'Chung'):
                    if key in text:
                        hits.setdefault(key, []).append(os.path.relpath(path, root))
    for key in sorted(hits):
        print('\n"%s" referenced in: %s' % (key, ', '.join(sorted(hits[key])[:6])))
    OUT['source_hits'] = {k: sorted(v)[:6] for k, v in hits.items()}

    # ---- model trials ----------------------------------------------------
    table1 = {
        'O2': dict(Tc=154.58, pc=50.43e5, omega=0.0222, vc=73.529e-6),
        'CH4': dict(Tc=190.60, pc=46.10e5, omega=0.0110, vc=98.600e-6),
    }
    trials = []
    for name in ('O2', 'CH4'):
        thermo = gas.species(name).thermo
        coeffs = [[float(v) for v in c] for c in thermo.coeffs]
        ranges = [float(t) for t in thermo.temperature_ranges]
        for eos in ('IdealGas', 'RedlichKwong', 'PengRobinson'):
            for tr in ('mixture-averaged', 'high-pressure'):
                yaml = ['phases:',
                        '- name: probe',
                        '  thermo: {model: %s}' % eos,
                        '  species: [%s]' % name,
                        '  state: {T: 300.0, P: 56.0e5, X: {%s: 1.0}}' % name]
                if eos != 'IdealGas':
                    yaml.insert(3, '  transport: %s' % tr)
                else:
                    yaml.insert(3, '  transport: %s' % tr)
                yaml += ['species:', '- name: %s' % name,
                         '  thermo:',
                         '    model: NASA7',
                         '    temperature-ranges: [%s]' % ', '.join('%.2f' % t for t in ranges),
                         '    data:']
                for row in coeffs:
                    yaml.append('    - [%s]' % ', '.join('%.10e' % v for v in row))
                yaml += ['  transport:',
                         '    model: gas',
                         '    geometry: linear',
                         '    diameter: 3.0e-10',
                         '    well-depth: 100.0',
                         '    polarizability: 1.6',
                         '    rotational-relaxation: 1.0',
                         '  critical-parameters:',
                         '    critical-temperature: %.4f' % table1[name]['Tc'],
                         '    critical-pressure: %.6e' % table1[name]['pc'],
                         '    critical-volume: %.8e' % table1[name]['vc'],
                         '    acentric-factor: %.5f' % table1[name]['omega']]
                text = '\n'.join(yaml) + '\n'
                label = '%s/%s/%s' % (name, eos, tr)
                print('\n--- trial %s' % label)
                try:
                    phase = ct.Solution(yaml=text)
                    rows = []
                    for T in (120.0, 300.0):
                        phase.TP = T, 56.0e5
                        rows.append(dict(
                            T=T,
                            rho=float(phase.density),
                            cp=float(phase.cp_mass),
                            mu=float(phase.viscosity),
                            k=float(phase.thermal_conductivity),
                            Z=float(phase.compressibility),
                        ))
                    print('   ', json.dumps(rows))
                    trials.append(dict(label=label, ok=True, rows=rows))
                except BaseException as exc:            # noqa: BLE001
                    print('    FAILED %s: %s' % (type(exc).__name__, str(exc).splitlines()[0]))
                    trials.append(dict(label=label, ok=False,
                                       error='%s: %s' % (type(exc).__name__, exc)))
    OUT['trials'] = trials
    json.dump(OUT, open(os.path.join(os.environ.get('RUN_DIR', '.'), 'probe.json'), 'w'),
              indent=1)
    print('\nwrote probe.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
