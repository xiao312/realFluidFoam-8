"""Generate the OF8 contact-advection cases for `schmitt2020-fig-5`.

What the registered target states: p about 6 MPa, a density jump 1000 -> 100 kg/m3
with an error-function interface, uniform velocity 10 m/s, dx = 0.01 m, interface
resolved by n_x = 2, 4, 6 cells, t = 20 ms, and four panels (density, temperature,
pressure, velocity). The scientific content is in the pressure and velocity panels:
a consistent discretisation keeps both uniform while the contact advects.

What this generator can and cannot do with the frozen build: the built
`realFluidReactingFoam` uses `hePsiThermo` with `perfectGas`, so it has no real-fluid
equation of state. Oxygen at 6 MPa and 1000 kg/m3 is a supercritical liquid-like
state that an ideal gas cannot represent at any temperature, so the registered
thermodynamic state is **out of reach for this binary** and is recorded as a
blocker, not approximated silently. What is reachable, and is what these cases
measure, is the same numerical question in the solver's own validity envelope:

    periodic 1D domain, ideal gas, p = 1 atm, u = 10 m/s everywhere, and a smooth
    temperature contact 300 K -> 3000 K (a density ratio of 10, the same ratio the
    target uses) with an error-function profile of half-width n_x * dx.

A periodic domain is chosen deliberately: mass, momentum and total energy then have
no boundary flux at all, so their conservation is an exact statement rather than a
budget that needs boundary integrals, and the exact solution of the advection problem
is a rigid shift, T(x, t) = T0(x - u t), which gives a pointwise error metric. The
contact stays inside the domain for the whole 20 ms (it travels 0.2 m in a 0.6 m
domain starting at 0.15 m), so the periodic seam is never crossed.

Usage:
    python3 -B prepare_advection_case.py --out DIR --variant nx2|nx4|nx6 \
        --mechanism-source DIR_WITH_thermo.inputData_GRI [--source-commit SHA]
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

DX = 0.01
CELLS = 60
LENGTH = CELLS * DX
HEIGHT = 1e-5
DEPTH = 1e-5
PRESSURE = 101325.0
VELOCITY = 10.0
T_COLD = 300.0
T_HOT = 3000.0
INTERFACE_X = 0.15
END_TIME = 0.02
WRITE_INTERVAL = 0.005

VARIANTS = {
    'nx2': dict(interface_cells=2),
    'nx4': dict(interface_cells=4),
    'nx6': dict(interface_cells=6),
}

FOAMFILE = ('FoamFile\n{{\n    version 2.0;\n    format ascii;\n'
            '    class {cls};\n    object {obj};\n}}\n\n')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def species_names(thermo_text):
    m = re.search(r'\bspecies\s+(\d+)\s*\((.*?)\)\s*;', thermo_text, re.S)
    if not m:
        raise ValueError('no species list in thermo input')
    names = m[2].split()
    if len(names) != int(m[1]):
        raise ValueError('species count mismatch')
    return names


def cell_centres():
    return [(i + 0.5) * DX for i in range(CELLS)]


def temperature_profile(interface_cells):
    width = interface_cells * DX
    values = []
    for x in cell_centres():
        z = (x - INTERFACE_X) / width
        values.append(T_COLD + (T_HOT - T_COLD) * 0.5 * (1.0 + math.erf(z)))
    return values, width


def block_mesh():
    return FOAMFILE.format(cls='dictionary', obj='blockMeshDict') + (
        'convertToMeters 1;\n\n'
        'vertices\n(\n'
        '    (0 0 0)\n    ({L} 0 0)\n    ({L} {h} 0)\n    (0 {h} 0)\n'
        '    (0 0 {d})\n    ({L} 0 {d})\n    ({L} {h} {d})\n    (0 {h} {d})\n);\n\n'
        'blocks\n(\n    hex (0 1 2 3 4 5 6 7) ({n} 1 1) simpleGrading (1 1 1)\n);\n\n'
        'edges ();\n\n'
        'boundary\n(\n'
        '    left  {{ type cyclic; neighbourPatch right; faces ((0 4 7 3)); }}\n'
        '    right {{ type cyclic; neighbourPatch left; faces ((1 2 6 5)); }}\n'
        '    sides {{ type empty; faces ((0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); }}\n'
        ');\n\nmergePatchPairs ();\n'
    ).format(L=LENGTH, h=HEIGHT, d=DEPTH, n=CELLS)


def control_dict():
    return FOAMFILE.format(cls='dictionary', obj='controlDict') + (
        'application     realFluidReactingFoam;\n'
        'startFrom       startTime;\n'
        'startTime       0;\n'
        'stopAt          endTime;\n'
        'endTime         %r;\n'
        'deltaT          1e-06;\n'
        'writeControl    adjustableRunTime;\n'
        'writeInterval   %r;\n'
        'writeFormat     ascii;\n'
        'writePrecision  12;\n'
        'timePrecision   12;\n'
        'purgeWrite      0;\n'
        'adjustTimeStep  yes;\n'
        'maxCo           0.4;\n'
        'maxDeltaT       1e-04;\n'
        'runTimeModifiable true;\n'
    ) % (END_TIME, WRITE_INTERVAL)


def scalar_field(obj, values, dimensions, boundary):
    body = '\n'.join(repr(float(v)) for v in values)
    return FOAMFILE.format(cls='volScalarField', obj=obj) + (
        'dimensions      %s;\n' % dimensions) + (
        'internalField   nonuniform List<scalar>\n{n}\n(\n{body}\n)\n;\n'
        'boundaryField\n{{\n{bc}}}\n'
    ).format(n=len(values), body=body, bc=boundary)


def vector_field(obj, values, dimensions, boundary):
    body = '\n'.join('(%r %r %r)' % (v[0], v[1], v[2]) for v in values)
    return FOAMFILE.format(cls='volVectorField', obj=obj) + (
        'dimensions      %s;\n' % dimensions) + (
        'internalField   nonuniform List<vector>\n{n}\n(\n{body}\n)\n;\n'
        'boundaryField\n{{\n{bc}}}\n'
    ).format(n=len(values), body=body, bc=boundary)


def write_case(out, variant, mechanism_source, source_commit):
    cfg = VARIANTS[variant]
    constant = out / 'constant'
    system = out / 'system'
    zero = out / '0'
    for d in (constant, system, zero):
        d.mkdir(parents=True, exist_ok=True)

    copied = []
    for name in ('thermo.inputData_GRI', 'reactionsGRI', 'thermophysicalProperties',
                 'combustionProperties', 'momentumTransport'):
        src = mechanism_source / name
        if not src.exists():
            raise SystemExit('missing mechanism input %s' % src)
        (constant / name).write_bytes(src.read_bytes())
        copied.append(dict(name=name, sha256=sha256(src), bytes=src.stat().st_size))

    names = species_names((constant / 'thermo.inputData_GRI').read_text())

    (constant / 'chemistryProperties').write_text(
        FOAMFILE.format(cls='dictionary', obj='chemistryProperties') + (
            'chemistryType\n{\n    solver ode;\n    method idKineticStandard;\n}\n'
            'chemistry       off;\n'
            'initialChemicalTimeStep 1e-8;\n\n'
            'odeCoeffs\n{\n    solver seulex;\n    absTol 1e-8;\n    relTol 1e-6;\n}\n\n'
            '#include "reactionsGRI"\n'
        ))

    (system / 'blockMeshDict').write_text(block_mesh())
    (system / 'controlDict').write_text(control_dict())
    (system / 'fvSchemes').write_text(
        FOAMFILE.format(cls='dictionary', obj='fvSchemes') + (
            'ddtSchemes\n{\n    default Euler;\n}\n\n'
            'gradSchemes\n{\n    default Gauss linear;\n}\n\n'
            'divSchemes\n{\n    default Gauss linear;\n'
            '    div(phi,U) Gauss limitedLinearV 1;\n'
            '    div(phi,Yi_h) Gauss limitedLinear 1;\n'
            '    div(phid,p) Gauss upwind;\n}\n\n'
            'laplacianSchemes\n{\n    default Gauss linear corrected;\n}\n\n'
            'interpolationSchemes\n{\n    default linear;\n}\n\n'
            'snGradSchemes\n{\n    default corrected;\n}\n'
        ))
    (system / 'fvSolution').write_text(
        FOAMFILE.format(cls='dictionary', obj='fvSolution') + (
            'solvers\n{\n'
            '    "rho.*" { solver diagonal; }\n'
            '    p       { solver PCG; preconditioner DIC; tolerance 1e-8; relTol 0.05; }\n'
            '    pFinal  { $p; relTol 0; }\n'
            '    "(U|h|e)"      { solver PBiCGStab; preconditioner DILU; tolerance 1e-8; relTol 0.05; }\n'
            '    "(U|h|e)Final" { $U; relTol 0; }\n'
            '    "Yi.*"  { $hFinal; }\n'
            '}\n\n'
            'PIMPLE\n{\n    momentumPredictor yes;\n    nOuterCorrectors 1;\n'
            '    nCorrectors 2;\n    nNonOrthogonalCorrectors 0;\n}\n'
        ))

    cyclic = 'left { type cyclic; } right { type cyclic; } sides { type empty; }'
    temperatures, width = temperature_profile(cfg['interface_cells'])
    for name in names:
        value = {'O2': 0.23, 'N2': 0.77}.get(name, 0.0)
        (zero / name).write_text(scalar_field(name, [value] * CELLS,
                                              '[0 0 0 0 0 0 0]', cyclic))
    (zero / 'T').write_text(scalar_field('T', temperatures, '[0 0 0 1 0 0 0]', cyclic))
    (zero / 'p').write_text(FOAMFILE.format(cls='volScalarField', obj='p') + (
        'dimensions      [1 -1 -2 0 0 0 0];\n'
        'internalField   uniform %r;\n'
        'boundaryField\n{\n    left { type cyclic; } right { type cyclic; } '
        'sides { type empty; }\n}\n' % PRESSURE))
    (zero / 'U').write_text(vector_field(
        'U', [(VELOCITY, 0.0, 0.0)] * CELLS, '[0 1 -1 0 0 0 0]', cyclic))

    files = {}
    for path in sorted(out.rglob('*')):
        if path.is_file():
            files[str(path.relative_to(out))] = sha256(path)

    receipt = dict(
        schema='of8-advection-case-receipt-v1',
        case=str(out),
        variant=variant,
        target='schmitt2020-fig-5',
        source_commit=source_commit or 'unrecorded',
        frozen_inputs=copied,
        mechanism_species=len(names),
        mesh=dict(cells=CELLS, dx=DX, length=LENGTH, height=HEIGHT, depth=DEPTH,
                  left='cyclic', right='cyclic', sides='empty'),
        initial_state=dict(
            pressure_Pa=PRESSURE,
            velocity_m_per_s=[VELOCITY, 0.0, 0.0],
            temperature_cold_K=T_COLD,
            temperature_hot_K=T_HOT,
            interface='erf((x - %r)/width)' % INTERFACE_X,
            interface_x_m=INTERFACE_X,
            interface_cells=cfg['interface_cells'],
            interface_width_m=width,
            composition_mass_fraction={'O2': 0.23, 'N2': 0.77},
            density_ratio_ideal_gas=T_HOT / T_COLD,
        ),
        chemistry='off',
        controls=dict(startFrom='startTime', startTime=0.0, stopAt='endTime',
                      endTime=END_TIME, deltaT_initial=1e-6, adjustTimeStep='yes',
                      maxCo=0.4, maxDeltaT=1e-4, writeInterval=WRITE_INTERVAL,
                      expected_writes=int(round(END_TIME / WRITE_INTERVAL))),
        expected_conserved_quantity=(
            'periodic domain: no boundary flux of mass, momentum or energy, so '
            'sum(rho)*V, sum(rho*U)*V and sum(rho*(hs + hf - p/rho + 0.5*|U|^2))*V '
            'must be constant; with chemistry off hs + hf is the total enthalpy'),
        exact_solution='T(x, t) = T0(x - %r t) modulo the periodic length %r m'
                       % (VELOCITY, LENGTH),
        scope=('numerics-only stand-in: the built solver has no real-fluid equation of '
               'state, so the registered 6 MPa O2 density jump 1000 -> 100 kg/m3 cannot '
               'be reproduced; the density ratio 10, dx = 0.01 m, n_x = 2/4/6, u = 10 m/s '
               'and t = 20 ms are matched. No figure replication claim, no acceptance.'),
        files=files,
        file_count=len(files),
    )
    receipt_path = Path(str(out) + '.receipt.json')
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(case=str(out), variant=variant, files=len(files),
                          interface_width_m=width,
                          controls=receipt['controls'], receipt=str(receipt_path)),
                     indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--variant', choices=sorted(VARIANTS), required=True)
    parser.add_argument('--mechanism-source', type=Path, required=True)
    parser.add_argument('--source-commit', default=None)
    args = parser.parse_args()
    write_case(args.out, args.variant, args.mechanism_source, args.source_commit)


if __name__ == '__main__':
    main()
