"""Generate the small time-zero energy/inversion cases for the OF8 diagnostic.

Why this exists: the 8000-cell slab of `of8-diag-v1` costs ~20 s per 1e-10 s step,
so a 7200 s allocation reached only 2.99e-8 s and saved one field. A conservation
diagnostic does not need 8000 cells or GRI ignition: it needs a case small enough
that the solver provably reaches `endTime` and writes every requested field, on a
mesh where the answer can be recomputed independently.

Two cases, both built here from inspectable dictionaries, both starting at
`startTime 0` with no carried-over field:

  A `chemOff`  32 cells, 4 mm slab, 1 atm methane/air (Y_CH4 0.055, Y_O2 0.220,
               Y_N2 0.725), initial temperature step 300 K | 1200 K, chemistry
               disabled, adiabatic walls, zero initial velocity. With chemistry
               off and no mass flux the mixture composition is frozen, so the
               conserved quantity is the sensible enthalpy integral
               `sum(rho * he) * V`; heat conduction may only rearrange it.

  B `chemOn`   32 cells, same slab and mixture, uniform 1500 K, chemistry on
               (GRI-3.0, seulex). Here sensible enthalpy is *not* conserved -
               chemical formation enthalpy is released - so the conserved
               quantity is the total energy including formation terms,
               `sum(rho * (ha - p/rho)) * V`.

Neither case claims a flame, a flame speed or convergence. The mechanism and
thermo dictionaries are copied byte-for-byte from the frozen case
(`--mechanism-source`), so the only new content is mesh, initial state and the
controller/chemistry switches listed in the receipt.

Usage:
    python3 -B prepare_energy_case.py --out DIR --variant chemOff|chemOn \
        --mechanism-source DIR_WITH_thermo.inputData_GRI [--source-commit SHA]
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

R_UNIVERSAL = 8314.46261815324  # J/(kmol K)

# Case definitions: everything here is declared in the receipt.
VARIANTS = {
    'chemOff': dict(
        chemistry='off',
        cells=32, length=0.004, height=1e-5, depth=1e-5,
        pressure=101325.0,
        temperature=dict(kind='step', cold=300.0, hot=1200.0),
        composition={'CH4': 0.055, 'O2': 0.220, 'N2': 0.725},
        end_time=1e-5, delta_t=1e-8, write_interval=2.5e-6,
        purpose='sensible-enthalpy conservation and inversion under conduction, chemistry frozen',
    ),
    'chemOn': dict(
        chemistry='on',
        cells=32, length=0.004, height=1e-5, depth=1e-5,
        pressure=101325.0,
        temperature=dict(kind='uniform', value=1500.0),
        composition={'CH4': 0.055, 'O2': 0.220, 'N2': 0.725},
        end_time=1e-6, delta_t=1e-8, write_interval=2.5e-7,
        purpose='total energy including formation enthalpy under GRI-3.0 heat release',
    ),
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


def block_mesh(cfg):
    n, length, h, d = cfg['cells'], cfg['length'], cfg['height'], cfg['depth']
    return FOAMFILE.format(cls='dictionary', obj='blockMeshDict') + (
        'convertToMeters 1;\n\n'
        'vertices\n(\n'
        '    (0 0 0)\n    ({L} 0 0)\n    ({L} {h} 0)\n    (0 {h} 0)\n'
        '    (0 0 {d})\n    ({L} 0 {d})\n    ({L} {h} {d})\n    (0 {h} {d})\n);\n\n'
        'blocks\n(\n    hex (0 1 2 3 4 5 6 7) ({n} 1 1) simpleGrading (1 1 1)\n);\n\n'
        'edges ();\n\n'
        'boundary\n(\n'
        '    left  {{ type patch; faces ((0 4 7 3)); }}\n'
        '    right {{ type patch; faces ((1 2 6 5)); }}\n'
        '    sides {{ type empty; faces ((0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); }}\n'
        ');\n\nmergePatchPairs ();\n'
    ).format(L=length, h=h, d=d, n=n)


def control_dict(cfg, application='realFluidReactingFoam'):
    return FOAMFILE.format(cls='dictionary', obj='controlDict') + (
        'application     {app};\n'
        'startFrom       startTime;\n'
        'startTime       0;\n'
        'stopAt          endTime;\n'
        'endTime         {end};\n'
        'deltaT          {dt};\n'
        'writeControl    runTime;\n'
        'writeInterval   {wi};\n'
        'writeFormat     ascii;\n'
        'writePrecision  12;\n'
        'timePrecision   12;\n'
        'purgeWrite      0;\n'
        'adjustTimeStep  no;\n'
        'maxCo           0.1;\n'
        'maxDeltaT       5e-08;\n'
        'runTimeModifiable true;\n'
    ).format(app=application, end=cfg['end_time'], dt=cfg['delta_t'], wi=cfg['write_interval'])


def scalar_field(obj, values, boundary, dimensions='[0 0 0 0 0 0 0]'):
    body = '\n'.join(repr(float(v)) for v in values)
    return FOAMFILE.format(cls='volScalarField', obj=obj) + (
        'dimensions      %s;\n' % dimensions) + (
        'internalField   nonuniform List<scalar>\n{n}\n(\n{body}\n)\n;\n'
        'boundaryField\n{{\n{bc}}}\n'
    ).format(n=len(values), body=body, bc=boundary)


def vector_field(obj, values, boundary):
    body = '\n'.join('(%r %r %r)' % (v[0], v[1], v[2]) for v in values)
    return FOAMFILE.format(cls='volVectorField', obj=obj) + (
        'dimensions      [0 1 -1 0 0 0 0];\n'
        'internalField   nonuniform List<vector>\n{n}\n(\n{body}\n)\n;\n'
        'boundaryField\n{{\n{bc}}}\n'
    ).format(n=len(values), body=body, bc=boundary)


def temperature_profile(cfg):
    n = cfg['cells']
    spec = cfg['temperature']
    if spec['kind'] == 'uniform':
        return [spec['value']] * n
    if spec['kind'] == 'step':
        half = n // 2
        return [spec['cold']] * half + [spec['hot']] * (n - half)
    raise ValueError('unknown temperature profile')


def write_case(out, variant, mechanism_source, source_commit):
    cfg = VARIANTS[variant]
    n = cfg['cells']
    constant = out / 'constant'
    system = out / 'system'
    zero = out / '0'
    for d in (constant, system, zero):
        d.mkdir(parents=True, exist_ok=True)

    # mechanism/thermo dictionaries: byte copies, never regenerated
    copied = []
    for name in ('thermo.inputData_GRI', 'reactionsGRI', 'thermophysicalProperties',
                 'combustionProperties', 'momentumTransport'):
        src = mechanism_source / name
        if not src.exists():
            raise SystemExit('missing mechanism input %s' % src)
        (constant / name).write_bytes(src.read_bytes())
        copied.append(dict(name=name, sha256=sha256(src), bytes=src.stat().st_size))

    thermo_text = (constant / 'thermo.inputData_GRI').read_text()
    names = species_names(thermo_text)

    # chemistry switch is the only edited constant dictionary
    (constant / 'chemistryProperties').write_text(
        FOAMFILE.format(cls='dictionary', obj='chemistryProperties') + (
            'chemistryType\n{{\n    solver ode;\n    method idKineticStandard;\n}}\n'
            'chemistry       {onoff};\n'
            'initialChemicalTimeStep 1e-8;\n\n'
            'odeCoeffs\n{{\n    solver seulex;\n    absTol 1e-8;\n    relTol 1e-6;\n}}\n\n'
            '#include "reactionsGRI"\n'
        ).format(onoff=cfg['chemistry']))

    (system / 'blockMeshDict').write_text(block_mesh(cfg))
    (system / 'controlDict').write_text(control_dict(cfg))
    (system / 'fvSchemes').write_text(
        FOAMFILE.format(cls='dictionary', obj='fvSchemes') + (
            'ddtSchemes\n{\n    default Euler;\n}\n\n'
            'gradSchemes\n{\n    default Gauss linear;\n}\n\n'
            'divSchemes\n{\n    default Gauss linear;\n'
            '    div(phi,U) Gauss limitedLinearV 1;\n'
            '    div(phi,Yi_h) Gauss limitedLinear 1;\n}\n\n'
            'laplacianSchemes\n{\n    default Gauss linear corrected;\n}\n\n'
            'interpolationSchemes\n{\n    default linear;\n}\n\n'
            'snGradSchemes\n{\n    default corrected;\n}\n'
        ))
    (system / 'fvSolution').write_text(
        FOAMFILE.format(cls='dictionary', obj='fvSolution') + (
            'solvers\n{\n'
            '    "rho.*" { solver diagonal; }\n'
            '    p       { solver PCG; preconditioner DIC; tolerance 1e-7; relTol 0.1; }\n'
            '    pFinal  { $p; relTol 0; }\n'
            '    "(U|h|e)"      { solver PBiCGStab; preconditioner DILU; tolerance 1e-7; relTol 0.1; }\n'
            '    "(U|h|e)Final" { $U; relTol 0; }\n'
            '    "Yi.*"  { $hFinal; }\n'
            '}\n\n'
            'PIMPLE\n{\n    momentumPredictor yes;\n    nOuterCorrectors 1;\n'
            '    nCorrectors 2;\n    nNonOrthogonalCorrectors 0;\n}\n'
        ))

    # Closed box: adiabatic, impermeable, rigid walls. A waveTransmissive patch would let
    # mass and energy leave the domain, which would contradict the declared conserved
    # quantity (sum(rho*he)*V with no mass flux) and turn any conservation statement into a
    # boundary-flux statement that this case does not measure.
    wall = 'left { type zeroGradient; } right { type zeroGradient; } sides { type empty; }'
    pressure_wall = 'left { type zeroGradient; } right { type zeroGradient; } sides { type empty; }'

    for name in names:
        values = [cfg['composition'].get(name, 0.0)] * n
        (zero / name).write_text(scalar_field(name, values, wall))
    (zero / 'T').write_text(scalar_field('T', temperature_profile(cfg), wall,
                                         dimensions='[0 0 0 1 0 0 0]'))
    (zero / 'p').write_text(FOAMFILE.format(cls='volScalarField', obj='p') + (
        'dimensions      [1 -1 -2 0 0 0 0];\n'
        'internalField   uniform %r;\n'
        'boundaryField\n{\n%s\n}\n' % (cfg['pressure'], pressure_wall)))
    (zero / 'U').write_text(vector_field('U', [(0.0, 0.0, 0.0)] * n,
                                         'left { type fixedValue; value uniform (0 0 0); } '
                                         'right { type fixedValue; value uniform (0 0 0); } '
                                         'sides { type empty; }'))

    files = {}
    for path in sorted(out.rglob('*')):
        if path.is_file():
            files[str(path.relative_to(out))] = sha256(path)

    composition_sum = sum(cfg['composition'].values())
    receipt = dict(
        schema='of8-energy-case-receipt-v1',
        case=str(out),
        variant=variant,
        source_commit=source_commit or 'unrecorded',
        purpose=cfg['purpose'],
        frozen_inputs=copied,
        mechanism_species=len(names),
        mesh=dict(cells=n, dx=cfg['length'] / n, length=cfg['length'],
                  height=cfg['height'], depth=cfg['depth']),
        initial_state=dict(
            pressure_Pa=cfg['pressure'],
            temperature=cfg['temperature'],
            composition_mass_fraction=cfg['composition'],
            composition_sum=composition_sum,
            velocity_m_per_s=[0.0, 0.0, 0.0],
        ),
        chemistry=cfg['chemistry'],
        energy_variable=(
            'he (sensibleEnthalpy): thermophysicalProperties declares '
            'energy sensibleEnthalpy, so he = hs and hf is excluded'),
        expected_conserved_quantity=(
            'chemistry off: sum(rho*he)*V with adiabatic, impermeable, rigid walls (p and T '
            'zeroGradient, U fixedValue 0) so there is no mass or energy flux; '
            'chemistry on: sum(rho*(ha - p/rho))*V, ha = hs + hf'),
        boundary_conditions=dict(p='zeroGradient', T='zeroGradient',
                                 species='zeroGradient', U='fixedValue (0 0 0)'),
        controls=dict(startFrom='startTime', startTime=0.0, stopAt='endTime',
                      endTime=cfg['end_time'], deltaT=cfg['delta_t'],
                      adjustTimeStep='no', writeInterval=cfg['write_interval'],
                      expected_writes=int(round(cfg['end_time'] / cfg['write_interval'])),
                      expected_steps=int(round(cfg['end_time'] / cfg['delta_t']))),
        files=files,
        file_count=len(files),
        scope=('single-rank bounded conservation/inversion diagnostic; no flame, '
               'no flame speed, no convergence or acceptance claim'),
    )
    receipt_path = Path(str(out) + '.receipt.json')
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(case=str(out), variant=variant, files=len(files),
                          controls=receipt['controls'], receipt=str(receipt_path)), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--variant', choices=sorted(VARIANTS), required=True)
    parser.add_argument('--mechanism-source', type=Path, required=True)
    parser.add_argument('--source-commit', default='')
    args = parser.parse_args()

    out = args.out.resolve()
    if out.exists():
        raise SystemExit('refusing to reuse existing output %s' % out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_case(out, args.variant, args.mechanism_source.resolve(), args.source_commit)


if __name__ == '__main__':
    main()
