"""Explicit paths, hashes and calibration shared by local replication tools."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPLICATION = HERE.parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def contained(root, path, exists=False):
    root = Path(root).resolve(strict=True)
    result = (root/path).resolve(strict=exists)
    if result == root or not result.is_relative_to(root):
        raise ValueError(f"Path must stay below project root: {result}")
    return result


def affine(value, calibration):
    """Convert physical values to PDF coordinates using two inspected ticks."""
    p0, v0, p1, v1 = calibration
    if v0 == v1 or p0 == p1:
        raise ValueError("Degenerate axis calibration")
    return p0+(value-v0)*(p1-p0)/(v1-v0)


class Inputs:
    def __init__(self, root):
        self.root = root
        self.hashes = {}

    def file(self, relative):
        path = contained(self.root, relative, exists=True)
        if not path.is_file():
            raise ValueError(f"Expected input file: {path}")
        self.hashes[str(path.relative_to(self.root))] = digest(path)
        return path

    def verify(self):
        for relative, expected in self.hashes.items():
            if digest(self.root/relative) != expected:
                raise ValueError(f"Input changed during analysis: {relative}")
