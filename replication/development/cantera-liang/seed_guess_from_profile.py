"""Build an initial-guess table for a stage from a converged profile of another stage.

Why: stage 5 (the full binary diffusion matrix) has never produced a point at 100 atm. Four
bounded attempts spent the whole budget on the first steady solve, starting from the frozen
2126-point ideal guess and, in the last attempt, from a 2126-point ideal-flame table whose
reaction zone is far too thin for 100 atm. Both the grid size and the distance of the initial
guess from the stage-5 solution are candidate causes, and neither has been separated.

This tool changes only the initial guess. It reads a converged `profile.csv` (the output format
the driver itself writes), maps its columns onto the frozen guess layout
(`x_m,T_K,U_m_s,rho_kg_m3,Qdot_W_m3` followed by the species mass fractions), keeps a
subsampled set of whole rows, and refuses to write a table that breaks any check the frozen
`prepare_guess.py` makes: monotone abscissa, both boundary rows kept, non-negative and
summable mass fractions, and a coarse grid that still follows the source temperature curve to
within 5 K. No row is ever synthesised, and the energy term is set to zero because the guess
layout carries it only for shape; the driver ignores columns 3 and 4 and reads species from
column 5 onwards.

    python3 seed_guess_from_profile.py PROFILE_CSV DST_DIR --points 400

The physical state at every retained row is exactly a row of the source profile, so the
converged solution of the seeded run is the solution of the same model: only the path differs.
"""
import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from prepare_guess import check, read_table, subsample  # noqa: E402

STATE = ['x_m', 'T_K', 'U_m_s', 'rho_kg_m3']
FROZEN_STATE = ['x_m', 'T_K', 'U_m_s', 'rho_kg_m3', 'Qdot_W_m3']


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('profile')
    ap.add_argument('dst')
    ap.add_argument('--points', type=int, default=400)
    a = ap.parse_args(argv)

    src = pathlib.Path(a.profile)
    header, rows, raw = read_table(src)
    if header[:4] != STATE:
        sys.exit('unexpected profile layout: %r' % header[:4])
    species = [name[2:] for name in header if name.startswith('Y_')]
    if not species:
        sys.exit('profile has no Y_ columns')

    # Frozen guess layout: state, a placeholder energy column, then bare species names.
    frozen = FROZEN_STATE + species
    # Map each source row onto the frozen guess layout before checking it, so the checks see
    # exactly the numbers the driver will read.
    guess = []
    for row in rows:
        fields = [row[0], row[1], row[2], row[3], 0.0]
        fields += [row[k] for k in range(4, len(header)) if header[k].startswith('Y_')]
        guess.append(fields)
    keep = subsample(guess, a.points)
    problems, worst_t, worst_sum, lowest = check(frozen, guess, keep)
    if problems:
        for p in problems:
            print('FAILED %s' % p, file=sys.stderr)
        sys.exit(1)

    dst = pathlib.Path(a.dst)
    dst.mkdir(parents=True, exist_ok=True)
    out = [','.join(frozen)]
    for i in keep:
        out.append(','.join('%.18e' % v for v in guess[i]))
    (dst / 'guess.csv').write_text('\n'.join(out) + '\n')

    report = dict(
        schema='forge-seeded-guess-v1',
        source_profile=str(src),
        source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        source_rows=len(rows), kept_rows=len(keep), points=a.points,
        first_row_identical=keep[0] == 0, last_row_identical=keep[-1] == len(rows) - 1,
        max_temperature_interpolation_error_K=worst_t,
        max_mass_fraction_sum_error=worst_sum,
        most_negative_mass_fraction=None if lowest >= 0 else lowest,
        rows_are_verbatim_source_rows=True,
        note=('state and composition are exact rows of a converged profile; the energy column '
              'is zero because the driver reads only columns 0, 1, 2 and 5 onward'))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
