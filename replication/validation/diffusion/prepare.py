"""Create prescribed-state requests and independently evaluated correction factors."""
import argparse
import bisect
import csv
import json
from pathlib import Path


def correction(pr, tr, table):
    tr = min(max(tr, 1.0), 5.0)
    def node(row):
        _, limit, a, b, c, e = row
        return limit * (1-a*tr**(-b)) * (1-c*tr**(-e))
    if pr < table[0][0]:
        return 1.0
    if pr >= table[-1][0]:
        return node(table[-1])
    index = bisect.bisect_right([r[0] for r in table], pr)
    lower, upper = table[index-1:index+1]
    fraction = (pr-lower[0])/(upper[0]-lower[0])
    return node(lower)*(1-fraction)+node(upper)*fraction


def requests(inputs):
    table = json.loads(Path(__file__).with_name("references.json").read_text())["takahashi"]["table2"]
    species = {}
    for line in (inputs / "species.txt").read_text().splitlines():
        name, tc, pc, *_ = line.split()
        species[name] = (float(tc), float(pc))
    pressures = [r[0] for r in table]
    pressures += [(a[0]+b[0])/2 for a, b in zip(table, table[1:])]
    pressures += [.05, .099, .09999999, .10000001, 5.5]
    rows = []
    # Unequal pair fractions test pair normalization; trace limit tests bath mapping.
    for first, second, fraction in [("CH4", "N2", .5), ("H2", "N2", .2),
                                    ("OH", "N2", 1e-8)]:
        tc = fraction*species[first][0]+(1-fraction)*species[second][0]
        pc = fraction*species[first][1]+(1-fraction)*species[second][1]
        for pr in pressures:
            for tr in [.8, 1, 1.5, 2, 3, 5, 7]:
                rows.append(dict(first=first, second=second, fraction=fraction,
                                 temperature_K=tr*tc, pressure_Pa=pr*pc, Pr=pr, Tr=tr,
                                 expected_factor=correction(pr, tr, table),
                                 range_policy=pr < .1 or pr > 5 or tr < 1 or tr > 5))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = requests(args.inputs)
    if args.output is None:
        print(json.dumps(dict(requests=len(rows), inputs=str(args.inputs.resolve()),
                              output="none; plan only")))
        return
    with args.output.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
