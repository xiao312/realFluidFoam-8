#!/bin/bash
# Freeze the exact source a run uses into <run>/src and record its hashes before execution.
#
# The wrappers used to read /workspace/science directly, so a Git HEAD label in the receipt
# could disagree with what actually ran if the checkout moved during staging. This copies
# the named files from a named commit into the run directory, refuses to overwrite an
# existing freeze, and records SHA256 for every file. Downstream steps must use <run>/src.
set -euo pipefail
RUN=${1:?run directory}
SRC_COMMIT=${2:?source commit}
shift 2
FILES=("$@")
REPO=${REPO:-/workspace/science}
GIT=/workspace/.tooling/git-2.30.2/bin/git

head=$( cd "$REPO" && "$GIT" rev-parse HEAD )
if [ "$head" != "$SRC_COMMIT" ]; then
    echo "refusing to freeze: checkout HEAD $head != requested $SRC_COMMIT" >&2
    exit 1
fi
if [ -e "$RUN/src" ]; then
    echo "refusing to overwrite existing frozen source $RUN/src" >&2
    exit 1
fi
mkdir -p "$RUN/src"
for f in "${FILES[@]}"; do
    if ! ( cd "$REPO" && "$GIT" show "$SRC_COMMIT:replication/development/of8-clean-start/$f" ) \
            > "$RUN/src/$f"; then
        echo "cannot extract $f at $SRC_COMMIT" >&2
        exit 1
    fi
done
python3 - "$RUN/src" "$SRC_COMMIT" <<'PY' > "$RUN/src/SHA256SUMS"
import hashlib, sys
from pathlib import Path
d = Path(sys.argv[1])
print('# source_commit %s' % sys.argv[2])
for p in sorted(x for x in d.iterdir() if x.is_file() and x.name != 'SHA256SUMS'):
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    print('%s  %s' % (h, p.name))
PY
echo "frozen $SRC_COMMIT into $RUN/src ($(ls "$RUN/src" | wc -l) files)"
