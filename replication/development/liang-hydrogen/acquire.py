"""Acquire pinned author inputs and verify conversion; plan makes no writes."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen


AUTHOR_ROOT = "https://burke.me.columbia.edu/sites/default/files/content/"
SOURCES = {
    "burke-2012-chem.inp": (
        "chem.txt",
        "a68b12b089bb908242bf7673d6dfe34e4a08953dfcf3ba99da37b6db70d709d7"),
    "burke-2012-tran.dat": (
        "tran.txt",
        "35c110cd2275845c4f4e4d57325cb59e4065ac7403b641cbd1cb7a3e1f6ca783"),
    "burke-2012-author.cti": (
        "chem_cti.txt",
        "3648ea70bcf658ca6ba4b9e449e5a9f49ddf51999bad7bc60c1ad591442a5fbc"),
}
SPECIES = "H H2 O OH H2O O2 HO2 H2O2 N2 AR HE CO CO2".split()
FORMULA_REFERENCE = (
    "https://web.stanford.edu/group/haiwanglab/FFCM1/pages/transport.html")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_text(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path, data):
    write_text(path, json.dumps(data, indent=2) + "\n")


def acquire_sources(source_dir):
    """Verify all bytes before creating the output directory."""
    downloaded = {}
    for name, (relative_url, expected_hash) in SOURCES.items():
        if source_dir:
            raw = (source_dir / name).read_bytes()
        else:
            with urlopen(AUTHOR_ROOT + relative_url, timeout=30) as response:
                raw = response.read()
        actual_hash = digest(raw)
        if actual_hash != expected_hash:
            raise ValueError(
                f"{name}: SHA-256 changed ({actual_hash}); inspect the upstream "
                "revision before updating pins. No substitution is allowed.")
        downloaded[name] = raw
    return downloaded


def parse_transport(raw):
    """Separate conventional LJ rows and the author's four-row pair records."""
    lines = raw.decode("utf-8").splitlines()
    end = next(i for i, line in enumerate(lines) if line.strip() == "END")
    rows = {}
    for line in lines[:end]:
        fields = line.split("!", 1)[0].split()
        if fields and fields[0] in SPECIES:
            if len(fields) != 7 or fields[0] in rows:
                raise ValueError("Malformed or duplicate author LJ species row")
            rows[fields[0]] = line.rstrip()
    if set(rows) != set(SPECIES):
        raise ValueError("The author transport lacks expected species")
    records = []
    for number, line in enumerate(lines[end + 1:], start=end + 2):
        if line.strip() == "ENDDIFF":
            break
        code, _, comment = line.partition("!")
        if code.strip():
            records.append((number, code.split(), comment.strip()))
    else:
        raise ValueError("The author transport lacks ENDDIFF")
    if len(records) != 48:
        raise ValueError("Expected twelve four-row diffusion records")
    pairs = []
    for offset in range(0, len(records), 4):
        number, fields, comment = records[offset]
        if len(fields) != 6:
            raise ValueError(f"Malformed diffusion record at source line {number}")
        pair = fields[:2]
        item = {
            "pair": pair,
            "present_in_burke_mechanism": all(s in SPECIES for s in pair),
            "source_line": number,
            "reference_comment": comment,
            "D_coefficients": list(map(float, fields[2:])),
        }
        for index, label in enumerate(("Astar", "Bstar", "Cstar"), start=1):
            coefficients = records[offset + index][1]
            if len(coefficients) != 4:
                raise ValueError(f"Malformed {label} record after line {number}")
            item[label + "_coefficients"] = list(map(float, coefficients))
        pairs.append(item)
    if sum(item["present_in_burke_mechanism"] for item in pairs) != 10:
        raise ValueError("Expected ten applicable author diffusion pairs")
    document = {
        "source_url": AUTHOR_ROOT + SOURCES["burke-2012-tran.dat"][0],
        "source_sha256": digest(raw),
        "formula_reference": FORMULA_REFERENCE,
        "reference_pressure_Pa": 101325.0,
        "temperature_unit": "K",
        "log": "natural",
        "diffusivity_at_1atm_unit": "cm^2/s",
        "unit_reference": "https://www3.nd.edu/~powers/ame.60636/transport.pdf",
        "unit_qualification": "CGS Chemkin/Sandia convention; Wang specifies 1 atm",
        "formula_D_m2_s":
            "1e-4*101325/P_Pa*exp(d0+d1*ln(T)+d2*ln(T)^2+d3*ln(T)^3)",
        "cantera_m_bdiff_formula":
            "101325*1e-4*exp(d0+d1*ln(T)+d2*ln(T)^2+d3*ln(T)^3)",
        "collision_integrals_formula":
            "c0+c1*ln(T)+c2*ln(T)^2+c3*ln(T)^3; actual T, not reduced T",
        "temperature_validity_K": None,
        "liang_use_of_pair_extension": "unknown",
        "n_pairs_total": len(pairs),
        "n_pairs_available_in_burke": 10,
        "pairs": pairs,
    }
    return "\n".join(rows[name] for name in SPECIES) + "\n", document


def run_converter(output, module, arguments):
    result = subprocess.run(
        [sys.executable, "-B", "-m", module, *arguments], cwd=output,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    (output / (module.split(".")[-1] + ".log")).write_bytes(result.stdout)
    if result.returncode:
        raise RuntimeError(f"{module} failed; inspect its log in {output}")


def canonicalize_yaml(path):
    """Repair only the known nonnumeric bibliographic note; keep source bytes."""
    raw = path.read_bytes()
    malformed_note = b"5718\xef\xbf5727"
    repaired = raw.count(malformed_note)
    text = raw.replace(malformed_note, b"5718-5727").decode("utf-8")
    # Dates change on each conversion and are not a mechanism parameter.
    lines = [line for line in text.splitlines() if not line.startswith("date: ")]
    write_text(path, "\n".join(lines) + "\n")
    return repaired


def verify_conversion(output):
    import cantera as ct
    import numpy as np

    converted = ct.Solution(str(output / "burke-2012-lj-utf8.yaml"))
    reference = ct.Solution(str(output / "burke-2012-author-cti.yaml"))
    for gas in (converted, reference):
        if gas.species_names != SPECIES or gas.n_reactions != 27:
            raise ValueError("Expected the 13-species, 27-reaction author release")
    properties = (
        "forward_rate_constants", "reverse_rate_constants", "standard_cp_R",
        "standard_enthalpies_RT", "binary_diff_coeffs")
    errors = dict.fromkeys(properties, 0.0)
    for temperature in (300, 600, 1000, 1500, 2500, 3500):
        for pressure_atm in (1, 10, 100):
            for phi in (0.5, 1.0, 2.0):
                for gas in (converted, reference):
                    gas.set_equivalence_ratio(phi, "H2", "O2:1,N2:3.76")
                    gas.TP = temperature, pressure_atm * ct.one_atm
                for name in properties:
                    actual = np.asarray(getattr(converted, name))
                    expected = np.asarray(getattr(reference, name))
                    error = np.max(
                        np.abs(actual - expected) /
                        np.maximum(np.abs(expected), 1e-300))
                    if not np.isfinite(error) or error > 1e-12:
                        raise ValueError(f"Independent conversion differs: {name}")
                    errors[name] = max(errors[name], float(error))
    return {
        "cantera_version": ct.__version__, "states": 54,
        "species": SPECIES, "reaction_count": converted.n_reactions,
        "maximum_relative_errors": errors,
        "qualification": "Conversion consistency, not physical validation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "apply"))
    parser.add_argument("output", type=Path, help="New directory outside public Git")
    parser.add_argument(
        "--source-dir", type=Path,
        help="Offline directory containing the three pinned author files")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Choose a new output directory; existing inputs are immutable")
    if any((parent / ".git").exists() for parent in (output, *output.parents)):
        raise ValueError("Keep downloaded author inputs outside Git checkouts")
    plan = {
        "action": args.action, "output": str(output),
        "source_mode": "offline" if args.source_dir else "HTTPS author download",
        "sources": [
            {"file": name, "url": AUTHOR_ROOT + url, "sha256": sha}
            for name, (url, sha) in SOURCES.items()],
        "outputs": ["burke-2012-lj-utf8.yaml", "pair-coefficients.json",
                    "acquisition-manifest.json"],
        "transport": "LJ baseline plus separately extracted pair coefficients",
        "license": "Author copyright retained; redistribution license not established",
    }
    print(json.dumps(plan, indent=2))
    if args.action == "plan":
        if args.source_dir:
            acquire_sources(args.source_dir)
        return
    import cantera as ct
    if ct.__version__ != "3.2.0":
        raise ValueError("Use the pinned Cantera 3.2.0 Python environment")
    sources = acquire_sources(args.source_dir)
    lj_rows, pairs = parse_transport(sources["burke-2012-tran.dat"])
    output.mkdir(parents=True)
    for name, raw in sources.items():
        (output / name).write_bytes(raw)
    write_text(output / "burke-2012-lj-only.tran", lj_rows)
    write_json(output / "pair-coefficients.json", pairs)
    run_converter(output, "cantera.ck2yaml", [
        "--input=burke-2012-chem.inp",
        "--transport=burke-2012-lj-only.tran",
        "--output=burke-2012-lj-utf8.yaml"])
    run_converter(output, "cantera.cti2yaml", [
        "burke-2012-author.cti", "burke-2012-author-cti.yaml"])
    repaired = {}
    for name in ("burke-2012-lj-utf8.yaml", "burke-2012-author-cti.yaml"):
        repaired[name] = canonicalize_yaml(output / name)
    audit = verify_conversion(output)
    audit["source_pins"] = plan["sources"]
    audit["note_only_utf8_repairs"] = repaired
    audit["canonicalization"] = (
        "Known malformed Hong page-range dash replaced with ASCII hyphen; "
        "LF/UTF-8 output; generated date removed. Raw author files unchanged.")
    audit["files_sha256"] = {
        path.name: digest(path.read_bytes())
        for path in sorted(output.iterdir()) if path.is_file()}
    write_json(output / "acquisition-manifest.json", audit)
    print(json.dumps({"status": "verified", **audit}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"Acquisition failed: {error}") from error
