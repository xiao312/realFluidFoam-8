"""Optional hash-bound inlet scale; no ideal-gas planning-value fallback."""
import csv
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inlet_scale(case, statistics):
    unavailable = {'status': 'unavailable', 'reason': 'No executed inlet audit supplied',
                   'planningPlaceholderUsed': False, 'inputHashes': {}}
    if case is None:
        return unavailable
    case = Path(case)
    receipt_path = case / 'cold-initialization.json'
    input_path = case / 'direct-g2-input.json'
    if not receipt_path.is_file() or not input_path.is_file():
        return {**unavailable, 'reason': 'Executed initialization receipt or bound case input missing'}
    receipt = json.loads(receipt_path.read_text())
    raw_input_hash = digest(input_path)
    case_input = json.loads(input_path.read_text())
    if (receipt.get('schema') != 'direct-cold-ha-initialization/v1'
            or receipt.get('initialized') is not True or receipt.get('startTime') != 0
            or receipt.get('manifestSha256') != raw_input_hash
            or case_input != statistics['caseInput']
            or raw_input_hash not in statistics['inputHashes'].values()
            or str(receipt.get('jobId')) != str(statistics['runIdentity']['jobId'])):
        raise ValueError('Inlet normalization receipt is not bound to this executed case/job')
    hashes = {str(receipt_path.resolve()): digest(receipt_path), str(input_path.resolve()): raw_input_hash}
    ranks = receipt.get('ranks')
    if not isinstance(ranks, int) or ranks < 1:
        raise ValueError('Invalid inlet-audit rank count')
    rows = receipt.get('rankOutputs')
    if not rows and ranks == 1 and not receipt.get('boundaryAuditSha256'):
        return {**unavailable, 'reason': 'Serial initialization receipt has no boundary CSV hash binding',
                'inputHashes': hashes}
    if rows is None and ranks == 1 and receipt.get('boundaryAuditSha256'):
        rows = [{'rank': 0, 'boundaryAuditSha256': receipt['boundaryAuditSha256']}]
    if not isinstance(rows, list) or sorted(row.get('rank', -1) for row in rows) != list(range(ranks)):
        raise ValueError('Incomplete or duplicate receipt-bound inlet ranks')
    inputs = [(row, case / (f'processor{row["rank"]}' if ranks > 1 else '') / 'ha-initialization-boundaries.csv') for row in rows]
    missing = [str(path) for _, path in inputs if not path.is_file()]
    if missing:
        return {**unavailable, 'reason': 'Incomplete executed boundary audits', 'missingFiles': missing,
                'inputHashes': hashes}
    patches = []
    for rank, path in inputs:
        value = digest(path)
        if value != rank['boundaryAuditSha256']:
            raise ValueError('Changed executed boundary CSV: ' + str(path))
        hashes[str(path.resolve())] = value
        with path.open(newline='') as stream:
            data = list(csv.DictReader(stream))
        selected = [row for row in data if row.get('patch') == 'loxinlet']
        if len(selected) > 1:
            raise ValueError('Duplicate O2 inlet patch in rank audit')
        for row in selected:
            area, rho = float(row['area_m2']), float(row['rho_kg_m3'])
            if not math.isfinite(area) or not math.isfinite(rho) or area <= 0 or rho <= 0:
                raise ValueError('Invalid measured O2 inlet area/density')
            patches.append({'rank': rank['rank'], 'area_m2': area, 'rho_kg_m3': rho})
    if not patches:
        raise ValueError('No O2 inlet in complete executed boundary audits')
    area = math.fsum(row['area_m2'] for row in patches)
    rho_area = math.fsum(row['area_m2'] * row['rho_kg_m3'] for row in patches)
    mesh_patch = case_input['mesh']['patches']['loxinlet']
    expected_area = mesh_patch['area']
    diameter = 2 * mesh_patch['maxRadius']
    mass_flow = case_input['streams']['loxinlet']['massFlow_kg_s']
    if not all(math.isfinite(v) and v > 0 for v in [expected_area, diameter, mass_flow]):
        raise ValueError('Invalid bound mesh/flow metadata')
    if abs(area - expected_area) / expected_area > 1e-8:
        raise ValueError('Executed O2 inlet areas do not cover the bound mesh patch')
    if abs(mesh_patch['minRadius']) > 1e-12:
        raise ValueError('O2 patch is not the required disk inlet')
    rho_values = [row['rho_kg_m3'] for row in patches]
    if (max(rho_values) - min(rho_values)) / min(rho_values) > 1e-8:
        raise ValueError('Nonuniform initialized inlet density requires a separate velocity interpretation')
    return {'status': 'available-initialized-state-inference', 'velocity_m_s': mass_flow / rho_area,
            'diameter_m': diameter, 'massFlow_kg_s': mass_flow, 'measuredArea_m2': area,
            'rhoArea_kg_m': rho_area, 'rankPatchMeasurements': patches,
            'definition': 'Configured uniform O2 mass-flow inlet speed = mdot / sum(rho_initialized * area)',
            'paperInterpretation': 'Identifying paper u0 with our O2 bulk speed is an inference, not an explicit author value',
            'planningPlaceholderUsed': False, 'inputHashes': hashes}
