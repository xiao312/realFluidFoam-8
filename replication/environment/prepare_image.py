"""Download a pinned public image into a Docker archive without a Docker daemon."""
import concurrent.futures
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project-root', type=Path, required=True)
parser.add_argument('--apply', action='store_true', help='download and create the archive; default only prints the plan')
args = parser.parse_args()
root = args.project_root.resolve()
lock = json.loads((Path(__file__).parent / 'lock.json').read_text())
repository = lock['image'].removeprefix('docker.io/')
selection = {'image': repository, 'digest': lock['image_digest']}
cache = root / 'cache'
print(json.dumps({'root': str(root), 'cache': str(cache), 'image': repository,
                  'digest': selection['digest'], 'apply': args.apply}, indent=2), flush=True)
if not args.apply:
    raise SystemExit(0)
for child in ('cache', 'state'):
    path = root / child
    if path.resolve() != path:
        raise ValueError(f'Symlink escape: {path}')
    path.mkdir(parents=True, exist_ok=True)
token = json.load(urllib.request.urlopen(
    f'https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repository}:pull'))['token']
request = urllib.request.Request(
    f'https://registry-1.docker.io/v2/{repository}/manifests/{selection["digest"]}',
    headers={'Authorization': 'Bearer ' + token,
             'Accept': 'application/vnd.docker.distribution.manifest.v2+json'})
manifest_bytes = urllib.request.urlopen(request, timeout=90).read()
assert 'sha256:' + hashlib.sha256(manifest_bytes).hexdigest() == selection['digest']
manifest = json.loads(manifest_bytes)
(root / 'state/base-manifest.json').write_bytes(manifest_bytes)
(root / 'state/image-selection.json').write_text(json.dumps(selection, indent=2))

def download(entry):
    digest = entry['digest'].split(':')[1]
    path = cache / digest
    if not path.exists():
        request = urllib.request.Request(
            f'https://registry-1.docker.io/v2/{repository}/blobs/sha256:{digest}',
            headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(request, timeout=90) as response, path.with_suffix('.part').open('wb') as out:
            shutil.copyfileobj(response, out, 1024 * 1024)
        path.with_suffix('.part').replace(path)
    with path.open('rb') as source:
        actual = hashlib.file_digest(source, 'sha256').hexdigest()
    if actual != digest:
        raise ValueError(f'Blob digest mismatch: {digest}')
    print('Verified blob', digest[:12], path.stat().st_size, flush=True)
    return path

entries = [manifest['config'], *manifest['layers']]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(download, entries))
config = manifest['config']['digest'].split(':')[1]
config_data = json.loads((cache / config).read_text())
layers = []
for i, entry in enumerate(manifest['layers']):
    digest = entry['digest'].split(':')[1]
    output = cache / (digest + '.tar')
    if not output.exists():
        with gzip.open(cache / digest, 'rb') as src, output.open('wb') as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
    with output.open('rb') as src:
        actual = 'sha256:' + hashlib.file_digest(src, 'sha256').hexdigest()
    assert actual == config_data['rootfs']['diff_ids'][i]
    layers.append(output)
archive = cache / 'openfoam8-docker.tar.gz'
with tarfile.open(archive, 'w:gz', compresslevel=1) as tar:
    tar.add(cache / config, arcname=config + '.json')
    data = json.dumps([{'Config': config + '.json', 'RepoTags': [repository + ':pinned'],
                        'Layers': [p.name for p in layers]}]).encode()
    header = tarfile.TarInfo('manifest.json')
    header.size = len(data)
    tar.addfile(header, io.BytesIO(data))
    for path in layers:
        tar.add(path, arcname=path.name)
with archive.open('rb') as src:
    digest = hashlib.file_digest(src, 'sha256').hexdigest()
(root / 'state/archive.json').write_text(json.dumps({'file': archive.name, 'sha256': digest,
    'bytes': archive.stat().st_size, 'base_digest': selection['digest']}, indent=2))
(root / 'state/base-config.json').write_text(json.dumps(config_data, indent=2))
print('Archive complete', digest, flush=True)
