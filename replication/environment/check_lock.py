"""Check the recipe pins without network access or writes."""
import json
from pathlib import Path
import re

directory = Path(__file__).resolve().parent
lock = json.loads((directory / 'lock.json').read_text())
assert re.fullmatch(r'[0-9a-f]{40}', lock['upstream_revision'])
assert re.fullmatch(r'sha256:[0-9a-f]{64}', lock['image_digest'])
for name in ('Dockerfile', 'Apptainer.def'):
    assert lock['image_digest'] in (directory / name).read_text(), name
assert lock['expected_openfoam_version'] == '8'
print('PASS: source pin, OF8 identity, and both image recipes agree')
