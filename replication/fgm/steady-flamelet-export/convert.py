"""Strict retained-profile conversion; no integration or composition repair."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def element_coefficients(species):
    elements = list(dict.fromkeys(e for s in species for e in s['composition']))
    atomic_weights = {}
    for item in species:
        composition = item['composition']
        if len(composition) == 1:
            element, count = next(iter(composition.items()))
            if count == 1:
                atomic_weights[element] = item['molecularWeight_kg_kmol']
    require(set(elements) == set(atomic_weights), 'Missing monatomic species for exact elemental coefficients')
    for item in species:
        calculated = sum(atomic_weights[e]*n for e, n in item['composition'].items())
        require(abs(calculated-item['molecularWeight_kg_kmol']) < 1e-10,
                'Inconsistent molecular weight for '+item['name'])
    matrix = [[atomic_weights[e]*s['composition'].get(e, 0)/s['molecularWeight_kg_kmol']
               for s in species] for e in elements]
    require(max(abs(sum(row[j] for row in matrix)-1) for j in range(len(species))) < 1e-12,
            'Elemental coefficient columns do not sum to one')
    return elements, matrix


def load_inputs(args):
    directory = args.profile_dir
    paths = {name: directory/name for name in ('profile.csv', 'receipt.json', 'diagnostics.json')}
    receipt = json.loads(paths['receipt.json'].read_text(encoding='utf8'))
    metadata = json.loads(args.phase_metadata.read_text(encoding='utf8'))
    for name in ('profile.csv', 'diagnostics.json'):
        require(digest(paths[name]) == receipt['artifacts'][name], 'Receipt hash mismatch: '+name)
    require(receipt['source_commit'] == metadata['sourceCommit'], 'Source/phase mismatch')
    require(receipt['mechanism_sha256'] == metadata['mechanismSha256'], 'Mechanism/phase mismatch')
    require(receipt['coordinate'] == 'mixture_fraction' and receipt['status'] == 'steady_flamelet',
            'Input must be a retained steady-flamelet numerical profile')
    require(receipt.get('steady_numerically_converged') or args.allow_approximate,
            'Original steady check failed; --allow-approximate acknowledges it without changing the verdict')
    case = receipt['case']
    require((case['pressure_pa'], case['oxidizer']['temperature_k'], case['fuel']['temperature_k'])
            in [(5610000, 85, 288), (5600000, 83, 300)]
            and case['fuel']['mole_fractions'] == {'CH4': 1.0}
            and case['oxidizer']['mole_fractions'] == {'O2': 1.0}, 'Unsupported stream recipe')
    species = metadata['species']
    names = [s['name'] for s in species]
    require(len(names) == 53 and names == metadata['speciesOrder'] and len(set(names)) == 53,
            'Expected the exact 53-species GRI phase order')
    elements, coefficients = element_coefficients(species)
    with paths['profile.csv'].open(newline='', encoding='utf8') as handle:
        reader = csv.DictReader(handle)
        columns = ['Z_coordinate', 'T_K', 'Qdot_formation_298K_W_m3']+['Y_'+name for name in names]
        require(all(column in reader.fieldnames for column in columns), 'Missing required physical fields')
        rows = [[float(row[column]) for column in columns] for row in reader]
    require(len(rows) >= 2 and all(math.isfinite(v) for row in rows for v in row), 'Nonfinite/empty profile')
    require(rows[0][0] == 0 and rows[-1][0] == 1 and all(b[0] > a[0] for a, b in zip(rows, rows[1:])),
            'Z must strictly increase with exact zero/one endpoints')
    require(all(row[1] > 0 for row in rows), 'Nonpositive temperature')
    minimum = min(min(row[3:]) for row in rows)
    require(minimum >= 0, f'Negative physical mass fraction {minimum:.17g}; no repair is permitted')
    for row, name, temperature in [(rows[0], 'O2', case['oxidizer']['temperature_k']), (rows[-1], 'CH4', case['fuel']['temperature_k'])]:
        require(row[1] == temperature, 'Boundary temperature differs from original stream')
        require(all(y == (1.0 if n == name else 0.0) for n, y in zip(names, row[3:])),
                'Boundary composition is not the original pure stream')
    max_sum = max(abs(sum(row[3:])-1) for row in rows)
    element_errors = []
    for coefficient in coefficients:
        endpoint = [sum(a*b for a, b in zip(coefficient, row[3:])) for row in (rows[0], rows[-1])]
        element_errors.append(max(abs(sum(a*b for a, b in zip(coefficient, row[3:]))
                                  - ((1-row[0])*endpoint[0]+row[0]*endpoint[1])) for row in rows))
    require(max_sum <= 1e-8 and max(element_errors) <= 1e-8, 'Species/element conservation failed')
    chi = receipt['branch_case']['chi_st_s_inverse']
    require(math.isfinite(chi) and chi > 0, 'Invalid stoichiometric scalar dissipation')
    manifest = {
        'schema': 'steady-flamelet-export/v1', 'mode': 'fixed-chi-laminar-delta-PDF-diagnostic',
        'input_source_commit': receipt['source_commit'], 'input_case_id': receipt['branch_case']['id'],
        'case': case, 'chi_definition': 'stoichiometric', 'chi_value_s_inverse': chi,
        'chi_definition_evidence': 'direct-flamelet/paper_case.py passes stoich_dissipation_rate with Peters shape',
        'species': names, 'elements': elements, 'points': len(rows),
        'mechanism_sha256': receipt['mechanism_sha256'],
        'input_files': {name: digest(path) for name, path in paths.items()},
        'metadata_sha256': digest(args.phase_metadata),
        'original_steady_numerically_converged': receipt['steady_numerically_converged'],
        'original_physical_export_qualified': receipt.get('physical_export_qualified', False),
        'original_final_state_diagnostics': receipt['final_state_diagnostics'],
        'original_flamelet_seed': receipt.get('flamelet_seed'),
        'original_models': receipt['models'], 'spitfire_runtime': receipt['spitfire_runtime'],
        'checks': {'minimum_Y': minimum, 'species_sum_max_error': max_sum,
                   'element_max_errors': dict(zip(elements, element_errors)),
                   'maximum_temperature_K': max(row[1] for row in rows)},
        'composition_modified': False, 'nodes_resampled': False,
        'Q_policy': 'Retained formation-enthalpy source at 298.15K; diagnostic only, no extra Ha source',
        'T_policy': 'Retained ideal-gas diagnostic; CFD temperature remains thermophysical-model owned',
        'scientific_acceptance': False,
    }
    return rows, coefficients, manifest, paths


def table_text(rows, coefficients, manifest):
    numeric = lambda values: ' '.join(format(value, '.17g') for value in values)
    lines = ['FORGE_STEADY_FLAMELET 1', 'pressure-pa '+format(manifest['case']['pressure_pa'], '.17g'), 'chi-definition stoichiometric',
             'chi-value-s-1 '+format(manifest['chi_value_s_inverse'], '.17g'),
             'oxidizer-temperature-k '+format(manifest['case']['oxidizer']['temperature_k'], '.17g'),
             'fuel-temperature-k '+format(manifest['case']['fuel']['temperature_k'], '.17g'),
             'species '+str(len(manifest['species']))+' '+' '.join(manifest['species']),
             'elements '+str(len(manifest['elements']))+' '+' '.join(manifest['elements']),
             'element-mass-coefficients '+numeric([value for row in coefficients for value in row]),
             'points '+str(len(rows)), 'data']
    lines.extend(numeric(row) for row in rows)
    return '\n'.join(lines+['end', ''])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile-dir', required=True, type=Path)
    parser.add_argument('--phase-metadata', required=True, type=Path)
    parser.add_argument('--allow-approximate', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--source-commit')
    args = parser.parse_args()
    rows, coefficients, manifest, paths = load_inputs(args)
    content = table_text(rows, coefficients, manifest).encode('ascii')
    manifest['table_sha256'] = hashlib.sha256(content).hexdigest()
    manifest['converter_sha256'] = digest(Path(__file__))
    manifest['converter_source_commit'] = args.source_commit
    manifest['converter_identity_note'] = 'Exact converter file SHA256 binds this derivation; caller release verifies Git ancestry.'
    if args.apply:
        require(args.out is not None and not args.out.exists(), 'Apply requires a new output directory')
        require(re.fullmatch('[0-9a-f]{40}', args.source_commit or ''), 'Apply requires the exact converter --source-commit')
        args.out.mkdir(parents=True)
        (args.out/'steady.tbl').write_bytes(content)
        shutil.copyfile(paths['receipt.json'], args.out/'input-receipt.json')
        shutil.copyfile(paths['diagnostics.json'], args.out/'input-diagnostics.json')
        shutil.copyfile(args.phase_metadata, args.out/'phase-metadata.json')
        (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps({'read_only': not args.apply, **manifest}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
