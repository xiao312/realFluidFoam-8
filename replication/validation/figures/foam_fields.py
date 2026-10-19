"""Read ASCII pilot fields and calculate polyhedral cell centroids from the mesh."""
import re
from pathlib import Path
import numpy as np


def list_body(path):
    text = Path(path).read_text()
    match = re.search(r"\n\s*(\d+)\s*\n\(\s*\n(.*?)\n\)\s*", text, re.S)
    if not match:
        raise ValueError("Unsupported ASCII mesh list: " + str(path))
    return int(match.group(1)), match.group(2)


def field(path, count, vector=False):
    text = Path(path).read_text()
    uniform = re.search(r"internalField\s+uniform\s+([^;]+);", text)
    if uniform:
        values = np.fromstring(uniform.group(1).replace("(", "").replace(")", ""), sep=" ")
        return np.tile(values, (count, 1)) if vector else np.full(count, values[0])
    match = re.search(r"internalField\s+nonuniform\s+List<\w+>\s+(\d+)\s*\((.*?)\)\s*;", text, re.S)
    if not match or int(match.group(1)) != count:
        raise ValueError("Unsupported field or cell-count mismatch: " + str(path))
    values = np.fromstring(match.group(2).replace("(", " ").replace(")", " "), sep=" ")
    if values.size != count*(3 if vector else 1) or not np.isfinite(values).all():
        raise ValueError("Invalid field values: " + str(path))
    return values.reshape(count, 3) if vector else values


def centres(case):
    mesh = Path(case)/"constant/polyMesh"
    npoints, body = list_body(mesh/"points")
    points = np.fromstring(body.replace("(", " ").replace(")", " "), sep=" ").reshape(npoints, 3)
    nfaces, body = list_body(mesh/"faces")
    faces = [list(map(int, value.split())) for value in re.findall(r"\d+\(([^)]*)\)", body)]
    if len(faces) != nfaces:
        raise ValueError("Face count mismatch")
    _, body = list_body(mesh/"owner")
    owners = np.fromstring(body, sep=" ", dtype=int)
    _, body = list_body(mesh/"neighbour")
    neighbours = np.fromstring(body, sep=" ", dtype=int)
    count = int(max(owners.max(), neighbours.max()))+1
    volumes, moments = np.zeros(count), np.zeros((count, 3))
    for index, indices in enumerate(faces):
        polygon = points[indices]
        for i in range(1, len(polygon)-1):
            a, b, c = polygon[0], polygon[i], polygon[i+1]
            volume = np.dot(a, np.cross(b, c))/6
            moment = volume*(a+b+c)/4
            volumes[owners[index]] += volume
            moments[owners[index]] += moment
            if index < len(neighbours):
                volumes[neighbours[index]] -= volume
                moments[neighbours[index]] -= moment
    if not np.all(volumes > 0):
        raise ValueError("Nonpositive polyhedral cell volume")
    return moments/volumes[:, None]


def read_case(case):
    case = Path(case)
    xyz = centres(case)
    latest = max((path for path in case.iterdir() if path.is_dir() and re.fullmatch(r"[0-9.eE+-]+", path.name)),
                 key=lambda path: float(path.name))
    names = ("T", "rho", "Cp", "mu", "kappa", "CH4", "O2", "CO2", "H2O", "OH")
    fields = {name: field(latest/name, len(xyz)) for name in names}
    fields["U"] = field(latest/"U", len(xyz), vector=True)
    return xyz, fields, float(latest.name)


def read_decomposed(case, time, ranks=8):
    """Reassemble saved fields through global addresses, without OpenFOAM writes."""
    case = Path(case)
    xyz = centres(case)
    names = ('T', 'p', 'rho', 'Cp', 'mu', 'kappa', 'CH4', 'O2', 'CO2', 'H2O', 'OH', 'U')
    arrays = {n: np.full((len(xyz), 3) if n == 'U' else len(xyz), np.nan) for n in names}
    seen = np.zeros(len(xyz), dtype=int)
    for rank in range(ranks):
        proc = case / f'processor{rank}'
        count, text = list_body(proc / 'constant/polyMesh/cellProcAddressing')
        ids = np.fromstring(text, sep=' ', dtype=int)
        assert len(ids) == count and ids.min() >= 0 and ids.max() < len(xyz)
        seen[ids] += 1
        for name in names:
            arrays[name][ids] = field(proc / str(time) / name, count, vector=name == 'U')
    assert np.all(seen == 1) and all(np.isfinite(v).all() for v in arrays.values())
    return xyz, arrays, float(time)
