"""Prepare a narrow uncompiled cold arithmetic candidate; never mutate the source checkout."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
from common import sha256, write_json
from spitfire_patch import UPSTREAM

DIRECTORY = "src/spitfire/griffon/src/"
FILES = ["chemistry_kernels.cpp", "rates_sensitivities_exact.cpp",
         "rates_sensitivities_no_tbaf_sens.cpp", "rates_sensitivities_sparse.cpp"]
HEADER_NAME = "forge_stable_arrhenius.h"
CANDIDATE_PATCH_SHA256 = "9aa4ecfac5761f14d8bbf3cb757f4f77a0c8533f41626d443c30ba4da0f76af4"
HEADER = '''// Candidate numerical evaluation change; no thermodynamic or reaction coefficients changed.
#ifndef FORGE_STABLE_ARRHENIUS_H
#define FORGE_STABLE_ARRHENIUS_H
#include <array>
#include <cmath>
namespace griffon {
inline double forge_stable_arrhenius(const std::array<double, 3>& coefficients,
    double logT, double inverseT, double logFactor = 0.0, double multiplier = 1.0)
{
    if (coefficients[0] == 0.0 || multiplier == 0.0) return 0.0;
    const double exponent = coefficients[1] * logT - coefficients[2] * inverseT;
    // Preserve the established ordinary-temperature arithmetic exactly.
    if (logFactor == 0.0 && multiplier == 1.0 && std::abs(exponent) < 650.0)
        return coefficients[0] * std::exp(exponent);
    const double magnitude = std::exp(std::log(std::abs(coefficients[0])) + exponent
        + logFactor + std::log(std::abs(multiplier)));
    // No cap or replacement of material overflow. Negative A/multipliers retain their signs.
    return std::copysign(magnitude, coefficients[0]) * std::copysign(1.0, multiplier);
}
}
#endif
'''


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Expected one exact source anchor: {old[:80]}")
    return source.replace(old, new, 1)


def transform(name, text):
    text = replace_once(text, '#include "combustion_kernels.h"',
                        '#include "combustion_kernels.h"\n#include "' + HEADER_NAME + '"')
    anchor = "    const auto &kCoefs = rxnData.kFwdCoefs;"
    text = replace_once(text, anchor, anchor + '''
    const bool stableElementary = rxnData.type == RateType::SIMPLE
        || rxnData.type == RateType::THIRD_BODY;''')
    variable = "k" if name == "chemistry_kernels.cpp" else "kf"
    text = replace_once(text, f"      {variable} = ARRHENIUS(kCoefs);", f'''      {variable} = stableElementary
          ? forge_stable_arrhenius(kCoefs, logT, invT) : ARRHENIUS(kCoefs);''')
    if name == "chemistry_kernels.cpp":
        anchor = "      if (rxnData.reversible)\n      {\n        switch (n_net)"
        text = replace_once(text, anchor, '''      if (rxnData.reversible)
      {
        // The ordinary path retains existing third-body/falloff arithmetic.
        // Only simple/third-body reactions use the low-temperature logarithmic fallback.
        double inverseLogKc = rxnData.sumStoich * std::log(port);
        for (int n = 0; n < n_net; ++n)
          inverseLogKc -= invT * invGasConstant * net_stoich[n] * specG[net_indices[n]];
        if (stableElementary && std::abs(inverseLogKc) > 650.0)
        {
          double multiplier = 1.0;
          if (rxnData.type == RateType::THIRD_BODY)
          {
            multiplier = baseEff * conc;
            for (int n = 0; n < n_tb; ++n)
              multiplier += rho * tb_efficiencies[n] * y[tb_indices[n]];
          }
          kr = forge_stable_arrhenius(kCoefs, logT, invT, inverseLogKc, multiplier);
        }
        else switch (n_net)''')
    else:
        indent = "      " if name == "rates_sensitivities_no_tbaf_sens.cpp" else "        "
        replacement = '''// Keep the derivative equations and their third-body/falloff factors unchanged.
        // Use the same stable elementary reverse coefficient as the scalar RHS.
        double inverseLogKc = sumStoich * std::log(standardStatePressure * invT * invRu);
        for (int n = 0; n < n_net; ++n)
          inverseLogKc -= invT * invRu * net_stoich[n] * specG[net_indices[n]];
        kr = stableElementary && std::abs(inverseLogKc) > 650.0
            ? forge_stable_arrhenius(kCoefs, logT, invT, inverseLogKc) : kf / Kc;'''
        replacement = indent + replacement.replace("\n        ", "\n" + indent)
        text = replace_once(text, indent + "kr = kf / Kc;", replacement)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    head = subprocess.check_output(["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True).strip()
    if head != UPSTREAM:
        raise ValueError("Exact upstream base required")
    diff, manifest = [], {"schema": "spitfire-cold-candidate/v1", "upstream_revision": UPSTREAM,
        "status": "candidate_only_not_built_or_qualified", "files": {}, "source_mutated": False,
        "supported_path": "scalar production and dense/no-TBAF/sparse sensitivity kernels",
        "scope": "signed elementary/third-body Arrhenius evaluation; existing falloff and derivative formulas retained",
        "excluded_path": "legacy vectorized flamelet_rhs_test1", "scientific_acceptance": False,
        "script_sha256": sha256(__file__)}
    for name in FILES:
        relative = DIRECTORY + name
        original = (args.checkout / relative).read_bytes()
        authoritative = subprocess.check_output(["git", "-C", str(args.checkout), "show", UPSTREAM + ":" + relative])
        if original != authoritative:
            raise ValueError(f"Tracked source differs from exact base: {relative}")
        old = original.decode()
        new = transform(name, old)
        manifest["files"][relative] = {"original_sha256": hashlib.sha256(original).hexdigest(),
                                        "candidate_sha256": hashlib.sha256(new.encode()).hexdigest()}
        diff.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "a/" + relative, "b/" + relative))
    relative = DIRECTORY + HEADER_NAME
    manifest["files"][relative] = {"original_sha256": None, "candidate_sha256": hashlib.sha256(HEADER.encode()).hexdigest()}
    diff.extend(difflib.unified_diff([], HEADER.splitlines(True), "/dev/null", "b/" + relative))
    patch = "".join(diff)
    manifest["patch_sha256"] = hashlib.sha256(patch.encode()).hexdigest()
    if manifest["patch_sha256"] != CANDIDATE_PATCH_SHA256:
        raise ValueError("Generated patch differs from the explicitly frozen candidate")
    if args.plan:
        print(json.dumps(manifest, indent=2))
        return
    if args.out is None or args.out.exists():
        raise ValueError("--out must be a new directory")
    args.out.mkdir(parents=True)
    (args.out / "candidate.patch").write_bytes(patch.encode())
    write_json(args.out / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
