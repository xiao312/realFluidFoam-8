"""Prepare a steady FreeFlame guess from a completed project-owned profile."""
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'apply'])
    for name in ['base', 'profile', 'output']:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Output already exists')
    with args.profile.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    species = [line.split()[0] for line in (args.base/'species.txt').read_text().splitlines()]
    if len(species) != 53 or len(rows) < 10:
        raise ValueError('Expected 53 species and a completed spatial profile')
    for row in rows:
        values = [float(row['Y_'+name]) for name in species]
        if min(values) < -1e-9 or abs(sum(values)-1) > 1e-7:
            raise ValueError('Invalid composition in source profile')
    files = [args.profile] + [args.base/name for name in ['ideal.yaml', 'srk.yaml', 'species.txt']]
    receipt = {'purpose': 'steady numerical guess, not a transient restart',
               'points': len(rows), 'species': len(species),
               'inlet_mass_fractions': {name: float(rows[0]['Y_'+name]) for name in species},
               'inputs': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}
    print(json.dumps(receipt, indent=2))
    if args.action == 'plan':
        return
    args.output.mkdir(parents=True)
    for path in files[1:]:
        shutil.copyfile(path, args.output/path.name)
    with (args.output/'guess.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['x_m', 'T_K', 'U_m_s', 'rho_kg_m3', 'Qdot_placeholder'] + species)
        for row in rows:
            writer.writerow([row[name] for name in ['x_m', 'T_K', 'U_m_s', 'rho_kg_m3']]
                            + [0] + [row['Y_'+name] for name in species])
    (args.output/'guess-provenance.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    main()
