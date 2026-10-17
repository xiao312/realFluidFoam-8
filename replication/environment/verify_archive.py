"""Read-only check that a release archive preserves every tracked Git blob.

Run from the Git root: python3 -B replication/environment/verify_archive.py ARCHIVE REV
This detects Windows Git archive line-ending conversion and case-path loss.
"""
import hashlib
import subprocess
import sys
import tarfile
from pathlib import Path


def main():
    archive, revision = sys.argv[1:]
    tree = subprocess.check_output(["git", "ls-tree", "-rz", revision])
    entries = []
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        if kind != b"blob":
            raise ValueError("Submodules require a separate release manifest")
        entries.append((name.decode(), mode, oid))
    errors = []
    process = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE)
    try:
        with tarfile.open(archive) as package:
            members = {m.name: m for m in package.getmembers() if not m.isdir()}
            for name, mode, oid in entries:
                process.stdin.write(oid + b"\n")
                process.stdin.flush()
                header = process.stdout.readline().split()
                original = process.stdout.read(int(header[2]))
                process.stdout.read(1)
                member = members.pop(name, None)
                if member is None:
                    errors.append(f"missing: {name}")
                    continue
                actual = (member.linkname.encode() if mode == b"120000"
                          else package.extractfile(member).read())
                if actual != original:
                    errors.append(f"changed bytes: {name}")
            errors.extend(f"unexpected: {name}" for name in members)
    finally:
        process.stdin.close()
        process.stdout.close()
        process.wait()
    if errors:
        print("\n".join(errors[:15]))
        raise SystemExit(f"FAIL: {len(errors)} archive differences")
    with Path(archive).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    print(f"PASS: {len(entries)} Git blobs preserved; SHA-256 {digest}")


if __name__ == "__main__":
    main()
