"""Read-only verification of a Linux build tree against a Git source archive."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tarfile


def audit(archive, tree):
    tree = Path(tree).resolve(strict=True)
    errors, normalized, groups = [], [], {}
    checked_files = 0
    directory_entries = {}
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        for member in members:
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe archive path: " + member.name)
            current = tree
            for component in relative.parts:
                if current not in directory_entries:
                    directory_entries[current] = set(os.listdir(current)) if current.is_dir() else set()
                if component not in directory_entries[current]:
                    errors.append({"path": member.name, "reason": "missing exact-case component", "component": component})
                    break
                current = current / component
            else:
                if member.isfile():
                    checked_files += 1
                    expected = source.extractfile(member).read()
                    actual = current.read_bytes()
                    if actual != expected:
                        entry = relative.suffix in (".sh", ".in") or relative.name.startswith("Allw")
                        if entry and actual == expected.replace(b"\r\n", b"\n"):
                            normalized.append(member.name)
                        else:
                            errors.append({"path": member.name, "reason": "content mismatch"})
                elif member.issym() and (not current.is_symlink() or os.readlink(current) != member.linkname):
                    errors.append({"path": member.name, "reason": "symlink mismatch"})
            # Include directory prefixes: case-colliding directories can contain
            # different basenames, so comparing complete file paths is insufficient.
            for length in range(1, len(relative.parts) + 1):
                path = str(PurePosixPath(*relative.parts[:length]))
                groups.setdefault(path.casefold(), set()).add(path)
    return {
        "archive_sha256": hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
        "checked_files": checked_files,
        "case_collision_groups": [sorted(paths) for paths in groups.values() if len(paths) > 1],
        "normalized_entry_files": normalized,
        "errors": errors,
        "passed": not errors,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: source_audit.py ARCHIVE LINUX_SOURCE_TREE")
    result = audit(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
