"""Plan or fetch the declared public NIST reference tables into project state."""
import argparse
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve(strict=True)
    output = (root/"state/nist-20261017").resolve()
    output.relative_to(root)
    params = dict(Action="Data", Wide="on", ID="C74828", Type="IsoBar", Digits="12", P=1,
                  TLow="180", THigh="620", TInc="10", RefState="DEF", TUnit="K",
                  PUnit="atm", DUnit="kg/m3", HUnit="kJ/kg", WUnit="m/s",
                  VisUnit="Pa*s", STUnit="N/m")
    records = []
    for pressure in (1, 50, 100, 200, 300):
        url = "https://webbook.nist.gov/cgi/fluid.cgi?" + urllib.parse.urlencode(dict(params, P=pressure), safe="*")
        path = output/("ch4-%satm.tsv" % pressure)
        print(path, url)
        if not args.apply:
            continue
        output.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError("Preserve existing reference retrieval: " + str(path))
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        for attempt in range(3):
            try:
                data = urllib.request.urlopen(request, timeout=30).read()
                break
            except urllib.error.HTTPError as error:
                if error.code < 500 or attempt == 2:
                    raise
        rows = list(csv.DictReader(io.StringIO(data.decode()), delimiter="\t"))
        assert len(rows) == 45 and "Cp (J/g*K)" in rows[0]
        assert all(abs(float(row["Pressure (atm)"])-pressure) < 1e-8 for row in rows)
        path.write_bytes(data)
        records.append(dict(file=path.name, url=url, sha256=hashlib.sha256(data).hexdigest(), rows=len(rows)))
    if args.apply:
        (output/"provenance.json").write_text(json.dumps(dict(
            retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            source="NIST Chemistry WebBook SRD 69; current retrieval, not the paper's 2017 snapshot",
            files=records), indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
