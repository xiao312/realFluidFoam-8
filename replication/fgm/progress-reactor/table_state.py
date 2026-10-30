"""Exact v2 Z/eta table interpolation; no extrapolation or hidden clipping."""
import hashlib
import numpy as np


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    header, blocks, block = {}, {}, None
    for line in path.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == 'block':
            block = ' '.join(words[1:])
            blocks[block] = []
        elif words[0] == 'end':
            block = None
        elif block:
            blocks[block].append([float(value) for value in words])
        else:
            header[words[0]] = words[1:]
    assert header['schema'] == ['forge-fgm-table-v2']
    axes = {key: np.array(header[key], float) for key in ('z', 'c', 'c-min', 'c-max')}
    assert np.all(np.diff(axes['z']) > 0) and np.all(np.diff(axes['c']) > 0)
    for name, values in blocks.items():
        blocks[name] = np.array(values)
        assert blocks[name].shape == (len(axes['z']), len(axes['c'])), name
        assert np.isfinite(blocks[name]).all(), name
    return header, axes, blocks


def sample(table, point):
    header, axes, blocks = table
    z, c = point['Z'], point['C']
    assert axes['z'][0] <= z <= axes['z'][-1]
    lower = float(np.interp(z, axes['z'], axes['c-min']))
    upper = float(np.interp(z, axes['z'], axes['c-max']))
    assert lower <= c <= upper and upper > lower
    eta = (c - lower)/(upper - lower)
    def interpolate(name):
        row = np.array([np.interp(z, axes['z'], blocks[name][:,j]) for j in range(len(axes['c']))])
        return float(np.interp(eta, axes['c'], row))
    fractions = {name: interpolate('Y '+name) for name in header['species']}
    assert min(fractions.values()) >= 0 and abs(sum(fractions.values())-1) <= 1e-10
    return {'Z': z, 'C_requested': c, 'Cmin': lower, 'Cmax': upper, 'eta': eta,
            'T_K': interpolate('Tdiag'), 'Y': fractions,
            'table_Sc_kg_m3_s': interpolate('Sc'), 'table_Qformation_W_m3': interpolate('Q'),
            'raw_species_sum': sum(fractions.values())}
