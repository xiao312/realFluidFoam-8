"""Verify retained paper assets against their preparation receipt and specification."""
import json
from pathlib import Path

from inputs import sha256


def load_targets(directory):
    directory = Path(directory)
    receipt_path = directory / 'receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    specification = Path(__file__).resolve().parent.parent / 'mascotte-review' / 'targets.json'
    if receipt.get('schema') != 'g2-paper-preparation/v1' or receipt.get('vector_curves') != 18:
        raise ValueError('Require the retained eighteen-curve Cavalieri preparation')
    retained_specification = directory / 'targets.json'
    if receipt.get('specification_sha256') != sha256(retained_specification):
        raise ValueError('Retained target specification hash differs from its receipt')
    # Windows checkout newline conversion changes bytes, not JSON content.
    if json.loads(retained_specification.read_text(encoding='utf-8')) != json.loads(specification.read_text(encoding='utf-8')):
        raise ValueError('Retained target specification content differs from the source catalogue')
    names = ['targets.json', 'cavalieri-curves.json', 'cavalieri2025-fig-6.png',
             'sharma2023-fig-9.png', 'singla2005-fig4cd-g2-ohstar.png', 'schmitt2020-fig-21.png']
    hashes = {str(receipt_path.resolve()): sha256(receipt_path), str(specification): sha256(specification)}
    for name in names:
        path = directory / name
        if sha256(path) != receipt['artifacts'].get(name):
            raise ValueError(f'Retained reference artifact hash mismatch: {name}')
        hashes[str(path.resolve())] = sha256(path)
    targets = json.loads(retained_specification.read_text(encoding='utf-8'))['targets']
    curves = json.loads((directory / 'cavalieri-curves.json').read_text(encoding='utf-8'))
    if curves.get('schema') != 'cavalieri-figure6-vectors/v1' or len(curves['curves']) != 18:
        raise ValueError('Incomplete Cavalieri reference curves')
    return {'targets': {item['id']: item for item in targets}, 'curves': curves['curves'],
            'hashes': hashes, 'directory': directory}
