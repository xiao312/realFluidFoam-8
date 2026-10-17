"""Fetch and verify the 901-state NIST nitrogen grid without silent resampling."""
import csv
import datetime
import hashlib
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
out = root/"state/figure-audit-20261017"
out.mkdir(exist_ok=True)
destination = out/"nitrogen-3.98MPa.tsv"
if destination.exists():
    raise FileExistsError(destination)
all_rows, records = [], []
for low, high in ((100, 212.5), (212.75, 325)):
    params = dict(Action="Data", Wide="on", ID="C7727379", Type="IsoBar", Digits=12,
                  P=3.98, TLow=low, THigh=high, TInc=0.25, RefState="DEF", TUnit="K",
                  PUnit="MPa", DUnit="kg/m3", HUnit="kJ/kg", WUnit="m/s", VisUnit="Pa*s", STUnit="N/m")
    url = "https://webbook.nist.gov/cgi/fluid.cgi?"+urllib.parse.urlencode(params, safe="*")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(request, timeout=45).read()
    rows = list(csv.DictReader(io.StringIO(raw.decode()), delimiter="\t"))
    expected = [low+index/4 for index in range(round((high-low)*4)+1)]
    if [float(row["Temperature (K)"]) for row in rows] != expected:
        raise ValueError("NIST resampled the requested temperature grid")
    if any(abs(float(row["Pressure (MPa)"])-3.98)>1e-10 for row in rows):
        raise ValueError("Incorrect pressure")
    name = f"nitrogen-{low}-{high}K.tsv"
    (out/name).write_bytes(raw)
    records.append(dict(file=name, url=url, sha256=hashlib.sha256(raw).hexdigest(), rows=len(rows)))
    all_rows.extend(rows)
with destination.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(all_rows[0]), delimiter="\t")
    writer.writeheader()
    writer.writerows(all_rows)
if len(all_rows) != 901:
    raise ValueError("Incomplete nitrogen grid")
manifest = dict(retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                sources=records, merged_file=destination.name,
                merged_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), rows=901)
(out/"nitrogen-reference.json").write_text(json.dumps(manifest, indent=2)+"\n")
print("Verified 901 NIST states at 3.98 MPa")
