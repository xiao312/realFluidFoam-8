"""Static admission checks for a generated OF8 case, run before the solver is started.

Why this exists: three mixing submissions died inside the solver or `blockMesh` for
dictionary reasons that are decidable without starting OpenFOAM at all (unterminated
controlDict, inlet patch sized with a cell list, a GRI reaction list referencing species
that the case's thermophysical table does not contain). Each failure cost one scheduler
slot. This module checks the generated case up front and, just as importantly, is tested
against a deliberately broken case so a silent pass cannot become the default.

Checks are structural only. They say nothing about whether a case is physically adequate.
"""
import re
from pathlib import Path

GRI_SOURCE = Path('/workspace/forge-out/runs/of8-case-v1/case/constant')


def _dict_entries_terminated(text):
    """Find a key/value line that is neither terminated by ';' nor opening a block.

    Targets only the failure mode that cost scheduler slots: an entry such as
    `deltaT  2e-07` with no trailing semicolon. FoamFile headers, `#include` lines,
    parenthesised lists spanning several lines and entries whose next line opens a `{`
    block are legal.
    """
    lines = text.splitlines()
    cleaned = [re.sub(r'//.*$', '', l).rstrip() for l in lines]
    balance = 0
    in_foamfile = False
    pending = None
    for idx, line in enumerate(cleaned):
        stripped = line.strip()
        if balance > 0:
            balance += stripped.count('(') - stripped.count(')')
            continue
        if not stripped:
            continue
        if stripped.startswith('FoamFile'):
            in_foamfile = True
            continue
        if in_foamfile:
            if stripped == '}':
                in_foamfile = False
            continue
        if stripped.startswith('#'):
            continue
        if stripped in ('(', ')', '{', '}') or stripped.startswith('('):
            balance += stripped.count('(') - stripped.count(')')
            continue
        rest = [l.strip() for l in cleaned[idx + 1:] if l.strip()]
        nxt = rest[0] if rest else ''
        if nxt.startswith(('{', '(', '[')):
            continue
        # a size line followed by the list it introduces, e.g. "coeffs / 53 / ("
        if re.fullmatch(r'-?\d+', nxt) and len(rest) > 1 and rest[1].startswith('('):
            continue
        if stripped.endswith((';', '{', '}')):
            continue
        return 'line %d not terminated: %r' % (idx + 1, lines[idx])
    return None


def species_list(case):
    text = (case / 'constant' / 'thermophysicalProperties').read_text()
    m = re.search(r'species\s*\(([^)]*)\)', text)
    if m:
        return m[1].split()
    # thermo type files carry no explicit list: the species are the thermo blocks
    names = sorted(thermo_species(case))
    if not names:
        raise ValueError('no species list in thermophysicalProperties and no thermo blocks')
    return names


def thermo_species(case):
    text = (case / 'constant' / 'thermo.inputData_GRI').read_text()
    m = re.search(r'species\s+\d+\s*\(([^)]*)\)', text)
    if m:
        return set(m[1].split())
    m = re.search(r'species\s*\n\s*(\d+)\s*\n\(', text)
    if m:
        names = text[m.end():].split()[:int(m[1])]
        if len(names) == int(m[1]) and all(re.fullmatch(r'[A-Za-z][A-Za-z0-9()]*', n)
                                           for n in names):
            return set(names)
    names = set()
    for m in re.finditer(r'^\s*([A-Za-z][A-Za-z0-9()]*)\s*\n\s*\{\s*\n\s*lowCoeffs', text, re.M):
        names.add(m[1])
    return names


def reaction_species(case):
    """Species named in the reaction list, using the full mechanism list to tokenise."""
    path = case / 'constant' / 'reactionsGRI'
    text = path.read_text()
    if 'reactions ();' in text or not re.search(r'reaction\s+"', text):
        return set()
    full = set(reaction_species_reference())
    found = set()
    for m in re.finditer(r'reaction\s+"([^"]+)"', text):
        for token in re.split(r'[+\s<=>]+', m[1]):
            if token and token in full:
                found.add(token)
    return found


_cache = {}


def reaction_species_reference():
    """Species named anywhere in the source mechanism's reaction list."""
    if 'ref' not in _cache:
        text = (GRI_SOURCE / 'reactionsGRI').read_text()
        names, _ = thermo_names(GRI_SOURCE)
        found = set()
        for m in re.finditer(r'reaction\s+"([^"]+)"', text):
            for token in re.split(r'[+\s<=>]+', m[1]):
                if token in names:
                    found.add(token)
        _cache['ref'] = sorted(found)
    return _cache['ref']


def thermo_names(directory):
    """Species names declared by a thermo data file (both header styles)."""
    text = (Path(directory) / 'thermo.inputData_GRI').read_text()
    m = re.search(r'species\s+(\d+)\s*\(([^)]*)\)', text)
    if m:
        return m[2].split(), set(m[2].split())
    m = re.search(r'species\s*\n\s*(\d+)\s*\n\(', text)
    if m:
        names = text[m.end():].split()[:int(m[1])]
        return names, set(names)
    names = re.findall(r'^\s*([A-Za-z][A-Za-z0-9()]*)\s*\n\s*\{\s*\n\s*lowCoeffs', text, re.M)
    return names, set(names)


def patch_sizes(case):
    """Face count carried by each 0/ field patch, e.g. {'inlet': 40, 'outlet': 40}.

    Field files may be written on one line, so the patch blocks are found by brace
    matching rather than by line layout.
    """
    out = {}
    for name in ('0/U', '0/T'):
        text = (case / name).read_text()
        pos = text.find('boundaryField')
        if pos < 0:
            continue
        body = text[pos:]
        for m in re.finditer(r'(\w+)\s*\{', body):
            block = body[m.end():]
            depth, endpos = 1, len(block)
            for i, ch in enumerate(block):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        endpos = i
                        break
            block = block[:endpos]
            n = re.search(r'nonuniform\s+List<\w+>\s+(\d+)', block)
            if n:
                out.setdefault(m[1], []).append(int(n[1]))
            elif re.search(r'uniform\s+\(', block):
                out.setdefault(m[1], []).append(1)
    return out


def reaction_list_form(directory):
    """`reactions` must be a dictionary block: ReactionList calls dict.subDict("reactions").

    Writing `reactions ();` (or any token list) produces a primitive entry, and the solver
    aborts while constructing the chemistry model with "Attempt to return primitive entry
    ITstream ... as a sub-dictionary" — job 125295010 failed exactly there.
    """
    problems = []
    for path in sorted(Path(directory).glob('*')):
        if not path.is_file():
            continue
        text = path.read_text(errors='replace')
        for m in re.finditer(r'^[ \t]*reactions[ \t]*\(', text, re.M):
            line = text[:m.start()].count('\n') + 1
            problems.append('%s:%d writes `reactions` as a token list; OpenFOAM requires a '
                            'dictionary block `reactions { ... }` (job 125295010 aborted here)'
                            % (path.name, line))
    return problems


def admission(case, expected_inlet_faces=None):
    """Return a list of hard failures; empty means the case passed static admission."""
    failures = []
    for name in ('system/controlDict', 'system/blockMeshDict', 'system/fvSchemes',
                 'system/fvSolution', 'constant/thermophysicalProperties',
                 'constant/thermo.inputData_GRI', 'constant/reactionsGRI'):
        path = case / name
        if not path.exists():
            failures.append('missing %s' % name)
            continue
        problem = _dict_entries_terminated(path.read_text())
        if problem:
            failures.append('%s: %s' % (name, problem))
    if failures:
        return failures

    names = set(species_list(case))
    table = thermo_species(case)
    if not names.issubset(table):
        failures.append('species without a thermo block: %s' % sorted(names - table))
    missing = reaction_species(case) - names
    if missing:
        failures.append('reaction species missing from the thermophysical table: %s'
                        % sorted(missing))
    failures.extend(reaction_list_form(case / 'constant'))
    for s in sorted(names):
        if not (case / '0' / s).exists():
            failures.append('no initial field 0/%s' % s)
    if expected_inlet_faces is not None:
        sizes = patch_sizes(case)
        for patch in ('inlet', 'outlet'):
            if patch in sizes and any(n != expected_inlet_faces for n in sizes[patch]):
                failures.append('%s patch is not %d faces: %s'
                                % (patch, expected_inlet_faces, sizes[patch]))
    return failures


def main(argv=None):
    import argparse, json, sys
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case', required=True, type=Path)
    ap.add_argument('--inlet-faces', type=int, default=None)
    args = ap.parse_args(argv)
    failures = admission(args.case, expected_inlet_faces=args.inlet_faces)
    sizes = patch_sizes(args.case)
    print(json.dumps({'case': str(args.case), 'patch_sizes': sizes,
                      'failures': failures}, indent=2))
    if failures:
        for f in failures:
            print('FAILED: ' + f, file=sys.stderr)
        return 1
    print('admission passed: %d species, patches %s'
          % (len(species_list(args.case)), sizes))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
