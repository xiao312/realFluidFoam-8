"""Build the initial flame profile for a high-pressure case from a coarser grid.

The frozen guess is a converged 1 atm ideal methane/air flame with 2126 grid points.
At 100 atm the reaction zone is roughly ten times thinner, so almost none of those
points resolve anything: they only enlarge every banded matrix the steady solver
factorises. In the registered `cantera32` image that made the run exceed the 1 GiB
per-rank limit (job 125208987 was killed with `OUT_OF_MEMORY` on 26 of 26 flames).

This tool subsamples the profile onto a coarser grid. It changes only the grid the
solver starts from - the species, the thermodynamic state at each retained row and
the boundary values are the frozen ones - so it is an initial-guess preparation
step, not a model change. Every retained row is an exact row of the frozen table.

    python3 prepare_guess.py SRC_DIR DST_DIR --points 400

The tool refuses to write a profile that breaks any check it can make locally:
non-monotone abscissa, missing endpoint, negative or non-summable mass fractions,
or a temperature shape that a linear interpolation of the coarse nodes cannot follow.
"""
import argparse
import hashlib
import json
import pathlib
import sys

# Columns written by the frozen table: state, then the 53 species mass fractions.
STATEFUL = ['x_m', 'T_K', 'U_m_s', 'rho_kg_m3', 'Qdot_W_m3']


def read_table(path):
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    header = lines[0].split(',')
    raw = lines[1:]
    rows = [ln.split(',') for ln in raw]
    for row in rows:
        if len(row) != len(header):
            raise SystemExit('row width %d != header width %d' % (len(row), len(header)))
    return header, [[float(v) for v in row] for row in rows], raw


def subsample(rows, count):
    if count >= len(rows):
        return list(range(len(rows)))
    # Even index spacing with both endpoints kept, so the inlet and outlet boundary
    # values the driver reads (values[2][0]) are exactly the frozen ones.
    last = len(rows) - 1
    return sorted({int(round(i * last / (count - 1))) for i in range(count)})


def check(header, rows, keep, tolerance=5.0):
    problems = []
    x = [rows[i][header.index('x_m')] for i in keep]
    if any(b <= a for a, b in zip(x, x[1:])):
        problems.append('abscissa is not strictly increasing')
    if keep[0] != 0 or keep[-1] != len(rows) - 1:
        problems.append('first or last grid point was dropped')
    species = [k for k, name in enumerate(header) if name not in STATEFUL]
    worst_sum = 0.0
    # The frozen table is solver output, so trace species carry undershoot of order
    # 1e-11. Anything below -1e-9 would be a broken row rather than round-off.
    lowest = 0.0
    for i in keep:
        total = sum(rows[i][k] for k in species)
        worst_sum = max(worst_sum, abs(total - 1.0))
        lowest = min(lowest, min(rows[i][k] for k in species))
    if lowest < -1e-9:
        problems.append('mass fraction of %.3e is below the round-off a converged '
                        'profile may carry' % lowest)
    if worst_sum > 1e-6:
        problems.append('mass fractions sum to 1 within only %.3e' % worst_sum)
    # The solver interpolates this table onto its own grid; a coarse node set that
    # cannot follow the frozen temperature curve would hand it a different flame. The
    # 5 K bound is 0.3 % of a 1500 K rise: a coarser grid may start further from the
    # solution but must not start from a different temperature profile.
    t = [rows[i][header.index('T_K')] for i in range(len(rows))]
    tx = [rows[i][header.index('x_m')] for i in range(len(rows))]
    kx = [rows[i][header.index('x_m')] for i in keep]
    kt = [rows[i][header.index('T_K')] for i in keep]
    worst = 0.0
    j = 0
    for xi, ti in zip(tx, t):
        while j + 1 < len(kx) - 1 and kx[j + 1] < xi:
            j += 1
        span = kx[j + 1] - kx[j]
        frac = 0.0 if span == 0 else (xi - kx[j]) / span
        worst = max(worst, abs(ti - (kt[j] + frac * (kt[j + 1] - kt[j]))))
    if worst > tolerance:
        problems.append('coarse nodes cannot follow the frozen temperature profile: '
                        'off by %.3f K' % worst)
    return problems, worst, worst_sum, lowest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--points', type=int, default=400)
    ap.add_argument('--name', default='guess.csv')
    a = ap.parse_args()
    src, dst = pathlib.Path(a.src), pathlib.Path(a.dst)
    header, rows, raw = read_table(src / a.name)
    # The frozen table is state columns followed by one column per species. A file
    # that does not start with the state columns is not this table, whatever its width.
    if header[:len(STATEFUL)] != STATEFUL or len(header) <= len(STATEFUL):
        raise SystemExit('unexpected table shape: %d columns starting with %r'
                         % (len(header), header[0]))
    keep = subsample(rows, a.points)
    problems, worst_t, worst_sum, lowest = check(header, rows, keep)
    if problems:
        for p in problems:
            print('FAILED %s' % p, file=sys.stderr)
        raise SystemExit(1)
    dst.mkdir(parents=True, exist_ok=True)
    # Copy the retained rows verbatim: the frozen digits are the input, not a
    # re-serialisation of them that happens to round-trip through a double.
    out = [','.join(header)] + [raw[i] for i in keep]
    (dst / a.name).write_text('\n'.join(out) + '\n')
    report = dict(schema='forge-guess-coarsening-v1', source=a.name,
                  source_sha256=hashlib.sha256((src / a.name).read_bytes()).hexdigest(),
                  source_rows=len(rows), kept_rows=len(keep), points=a.points,
                  first_row_identical=keep[0] == 0, last_row_identical=keep[-1] == len(rows) - 1,
                  max_temperature_interpolation_error_K=worst_t,
                  max_mass_fraction_sum_error=worst_sum,
                  most_negative_mass_fraction=None if lowest >= 0 else lowest,
                  rows_are_verbatim_source_lines=True,
                  note='retained rows are exact rows of the frozen table; only the grid changed')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
