"""Generate the bounded 2D two-stream cold-mixing case for the OF8 diagnostic track.

What this is, and what it is not
--------------------------------
The registered target `schmitt2020-fig-18-g2` is the Mascotte G2 case: LOx at 85 K and
5.59 MPa injected at 44.4 g/s into a coaxial CH4 stream at 288 K and 143.1 g/s. The frozen
build is `hePsiThermo` + `perfectGas` (`thermophysicalProperties` in the retained case
declares exactly that), so it cannot represent that state: LOx at 85 K and 5.59 MPa is a
supercritical liquid-like fluid (rho about 1140 kg/m3) whereas the ideal-gas value at the
same (T, p) is 254 kg/m3, a factor 4.5. That is recorded as a blocker, not approximated
away.

What the build *can* do is a two-stream cold-mixing diagnostic that keeps the registered
stream identity and the registered mass-flow ratio, in a gas-phase state the ideal-gas
thermodynamics is valid in:

  * fuel stream   CH4 at 288 K (the registered fuel temperature)
  * oxidiser      O2 at 100 K (the closest gas-phase analogue: at 1 atm oxygen at 85 K is
                  below its 90.19 K normal boiling point and is not a gas)
  * p = 101 325 Pa (the registered 5.59 MPa requires the real-fluid equation of state)
  * u_fuel = 10 m/s, and u_ox chosen so that (rho_ox u_ox A_ox)/(rho_fuel u_fuel A_fuel)
    equals the registered mass-flow ratio 44.4/143.1 = 0.31029 with equal stream areas

Both inlet velocities are imposed by a `fixedValue` inlet profile, so the inlet mass,
momentum and energy fluxes are known exactly from the dictionaries and can be compared
against the measured outlet flux and the measured accumulation. That is the point of the
case: a bounded mixing diagnostic with exact inlet fluxes, positivity, species closure and
a measurable imbalance - not a G2 replication. No OH, OH* or mean-field comparison is
claimed, and the temperatures, densities and Reynolds number are not the G2 ones.

Geometry: 2-D planar, x axial 0..L, y transverse 0..H, one cell thick in z (`empty`),
uniform mesh nx x ny. Inlet at x=0 with a nonuniform profile (fuel below mid-height,
oxidiser above), outlet at x=L with `p` fixedValue, transverse boundaries `slip`.

Usage:
    python3 -B prepare_mixing_case.py --out DIR --mechanism-source DIR [--nx 80 --ny 40]
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

R_UNIVERSAL = 8314.46261815324  # J/(kmol K)

DEFAULTS = dict(
    length=0.04,
    height=0.02,
    nx=80,
    ny=40,
    depth=1e-4,
    pressure=101325.0,
    fuel=dict(name='CH4', species='CH4', temperature=288.0, velocity=10.0),
    oxidiser=dict(name='O2', species='O2', temperature=100.0, velocity=None),
    # registered G2 mass flows; the oxidiser velocity is derived from their ratio
    g2_oxygen_mass_flow=44.4e-3,
    g2_fuel_mass_flow=143.1e-3,
    end_time=1e-3,
    delta_t=2e-7,
    write_interval=2e-4,
)

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


def specie_blocks(thermo_text):
    """Split a thermo.inputData file into its per-specie blocks (verbatim text)."""
    blocks = {}
    for m in re.finditer(r'^\s*([A-Za-z0-9_()+\-]+)\s*\{\s*specie\s*\{', thermo_text, re.M):
        name = m[1]
        depth = 0
        i = thermo_text.index('{', m.start())
        start = m.start()
        while i < len(thermo_text):
            if thermo_text[i] == '{':
                depth += 1
            elif thermo_text[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        blocks[name] = thermo_text[start:i + 1]
    return blocks


def write_thermo_subset(source_text, keep):
    """Write a thermo.inputData for `keep`, keeping each specie block byte-identical.

    The frozen GRI file carries 53 species. Transcribing that file for a 3-species cold
    mixing case would change coefficients; extracting the verbatim blocks keeps every
    coefficient exactly as the frozen mechanism states it and only changes which species
    are present. The receipt records both the source hash and the extracted blocks.
    """
    names = species_names(source_text)
    missing = [s for s in keep if s not in names]
    if missing:
        raise SystemExit('species not in the frozen thermo file: %s' % ', '.join(missing))
    blocks = specie_blocks(source_text)
    body = ['species %d (%s);\n' % (len(keep), ' '.join(keep))]
    for name in keep:
        body.append(blocks[name] + '\n')
    return ''.join(body)


def block_mesh(cfg):
    nx, ny, L, H, d = cfg['nx'], cfg['ny'], cfg['length'], cfg['height'], cfg['depth']
    return FOAMFILE.format(cls='dictionary', obj='blockMeshDict') + (
        'convertToMeters 1;\n\n'
        'vertices\n(\n'
        '    (0 0 0)\n    ({L} 0 0)\n    ({L} {H} 0)\n    (0 {H} 0)\n'
        '    (0 0 {d})\n    ({L} 0 {d})\n    ({L} {H} {d})\n    (0 {H} {d})\n);\n\n'
        'blocks\n(\n    hex (0 1 2 3 4 5 6 7) ({nx} {ny} 1) simpleGrading (1 1 1)\n);\n\n'
        'edges ();\n\n'
        'boundary\n(\n'
        '    inlet  {{ type patch; faces ((0 4 7 3)); }}\n'
        '    outlet {{ type patch; faces ((1 2 6 5)); }}\n'
        '    walls  {{ type patch; faces ((0 1 5 4) (3 7 6 2)); }}\n'
        '    front  {{ type empty; faces ((0 3 2 1)); }}\n'
        '    back   {{ type empty; faces ((4 5 6 7)); }}\n'
        ');\n\n'
        'mergePatchPairs ();\n'
    ).format(L=L, H=H, d=d, nx=nx, ny=ny)


def control_dict(cfg):
    return FOAMFILE.format(cls='dictionary', obj='controlDict') + (
        'application     realFluidReactingFoam;\n'
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
        'maxCo           0.5;\n'
        'maxDeltaT       5e-07;\n'
        'runTimeModifiable true;\n'
    ).format(end=cfg['end_time'], dt=cfg['delta_t'], wi=cfg['write_interval'])


def stream_properties(cfg):
    """Ideal-gas densities and the oxidiser velocity implied by the G2 mass-flow ratio."""
    p = cfg['pressure']
    fuel, ox = cfg['fuel'], cfg['oxidiser']
    weights = {'CH4': 16.043, 'O2': 31.998, 'N2': 28.014}
    rho_fuel = p * weights[fuel['species']] / (R_UNIVERSAL * fuel['temperature'])
    rho_ox = p * weights[ox['species']] / (R_UNIVERSAL * ox['temperature'])
    # equal stream areas (each occupies half the height), so the area cancels
    ratio = cfg['g2_oxygen_mass_flow'] / cfg['g2_fuel_mass_flow']
    u_ox = ratio * rho_fuel * fuel['velocity'] / rho_ox
    return dict(rho_fuel=rho_fuel, rho_ox=rho_ox, u_fuel=fuel['velocity'], u_ox=u_ox,
                mass_flow_ratio=ratio,
                inlet_mass_flux_fuel=rho_fuel * fuel['velocity'],
                inlet_mass_flux_ox=rho_ox * u_ox)


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


def uniform_profile(n, value):
    return [value] * n


def write_case(out, cfg, mechanism_source, source_commit):
    nx, ny, L, H = cfg['nx'], cfg['ny'], cfg['length'], cfg['height']
    n = nx * ny
    constant, system, zero = out / 'constant', out / 'system', out / '0'
    for d in (constant, system, zero):
        d.mkdir(parents=True, exist_ok=True)

    copied = []
    for name in ('thermophysicalProperties', 'combustionProperties', 'momentumTransport'):
        src = mechanism_source / name
        if not src.exists():
            raise SystemExit('missing mechanism input %s' % src)
        (constant / name).write_bytes(src.read_bytes())
        copied.append(dict(name=name, sha256=sha256(src), bytes=src.stat().st_size))

    # The GRI reaction list cannot be carried over: it references species (O, H, OH, CO2,
    # H2O, ...) that the three-species subset does not contain, and OpenFOAM aborts while
    # parsing it ("Specie O not found in table"). Job 125292279 died exactly there. With
    # CH4/O2/N2 only, no elementary reaction is representable at all, so this case is
    # generated with an empty reaction list and chemistry off, and the receipt says so.
    (constant / 'reactionsGRI').write_text(
        FOAMFILE.format(cls='dictionary', obj='reactionsGRI') +
        '// intentionally empty: the 3-species subset cannot represent a GRI reaction\n'
        'reactions ();\n')
    copied.append(dict(name='reactionsGRI',
                       sha256=sha256(constant / 'reactionsGRI'),
                       source_sha256=sha256(mechanism_source / 'reactionsGRI'),
                       note=('emptied: GRI reactions reference species outside the '
                             '3-species subset; this case is non-reacting by construction')))

    source_thermo = (mechanism_source / 'thermo.inputData_GRI')
    source_text = source_thermo.read_text()
    keep = [cfg['fuel']['species'], cfg['oxidiser']['species'], 'N2']
    keep = [s for i, s in enumerate(keep) if s not in keep[:i]]
    (constant / 'thermo.inputData_GRI').write_text(write_thermo_subset(source_text, keep))
    copied.append(dict(name='thermo.inputData_GRI (3-species subset, blocks verbatim)',
                       sha256=sha256(constant / 'thermo.inputData_GRI'),
                       source_sha256=sha256(source_thermo),
                       species=keep))

    (constant / 'chemistryProperties').write_text(
        FOAMFILE.format(cls='dictionary', obj='chemistryProperties') + (
            'chemistryType\n{\n    solver ode;\n    method idKineticStandard;\n}\n'
            'chemistry       off;\n'
            'initialChemicalTimeStep 1e-8;\n\n'
            'odeCoeffs\n{\n    solver seulex;\n    absTol 1e-8;\n    relTol 1e-6;\n}\n\n'
            '#include "reactionsGRI"\n'))

    props = stream_properties(cfg)
    (system / 'blockMeshDict').write_text(block_mesh(cfg))
    (system / 'controlDict').write_text(control_dict(cfg))
    (system / 'fvSchemes').write_text(
        FOAMFILE.format(cls='dictionary', obj='fvSchemes') + (
            'ddtSchemes\n{\n    default Euler;\n}\n\n'
            'gradSchemes\n{\n    default Gauss linear;\n}\n\n'
            'divSchemes\n{\n    default Gauss linear;\n'
            '    div(phi,U) Gauss upwind;\n'
            '    div(phi,Yi_h) Gauss upwind;\n}\n\n'
            'laplacianSchemes\n{\n    default Gauss linear corrected;\n}\n\n'
            'interpolationSchemes\n{\n    default linear;\n}\n\n'
            'snGradSchemes\n{\n    default corrected;\n}\n'))
    (system / 'fvSolution').write_text(
        FOAMFILE.format(cls='dictionary', obj='fvSolution') + (
            'solvers\n{\n'
            '    "rho.*" { solver diagonal; }\n'
            '    p       { solver PCG; preconditioner DIC; tolerance 1e-8; relTol 0.1; }\n'
            '    pFinal  { $p; relTol 0; }\n'
            '    "(U|h|e)"      { solver PBiCGStab; preconditioner DILU; tolerance 1e-8; relTol 0.1; }\n'
            '    "(U|h|e)Final" { $U; relTol 0; }\n'
            '    "Yi.*"  { $hFinal; }\n'
            '}\n\n'
            'PIMPLE\n{\n    momentumPredictor yes;\n    nOuterCorrectors 1;\n'
            '    nCorrectors 2;\n    nNonOrthogonalCorrectors 0;\n}\n'))

    fuel, ox = cfg['fuel'], cfg['oxidiser']
    # cell index = ix + nx*iy: the fuel stream occupies the lower half of the height
    is_fuel = [iy < ny // 2 for iy in range(ny)]
    T = []
    ux = []
    for iy in range(ny):
        for ix in range(nx):
            T.append(fuel['temperature'] if is_fuel[iy] else ox['temperature'])
            ux.append(props['u_fuel'] if is_fuel[iy] else props['u_ox'])

    # The inlet is the x = 0 patch, so it has ny faces, one per row, ordered by iy. The
    # internal field has nx*ny cells; using the cell list as the patch value is what job
    # 125291239 did, and OpenFOAM rejected it: "size 3200 is not equal to 40".
    T_inlet = [fuel['temperature'] if is_fuel[iy] else ox['temperature'] for iy in range(ny)]
    ux_inlet = [props['u_fuel'] if is_fuel[iy] else props['u_ox'] for iy in range(ny)]

    inlet = ('inlet { type fixedValue; value nonuniform List<%s> %d ( %s ); } '
             'outlet { type zeroGradient; } '
             'walls { type zeroGradient; } front { type empty; } back { type empty; }')
    for name in keep:
        values = [1.0 if (name == fuel['species'] and is_fuel[iy])
                  else (1.0 if (name == ox['species'] and not is_fuel[iy]) else 0.0)
                  for iy in range(ny) for ix in range(nx)]
        face_values = [1.0 if (name == fuel['species'] and is_fuel[iy])
                       else (1.0 if (name == ox['species'] and not is_fuel[iy]) else 0.0)
                       for iy in range(ny)]
        patch = (inlet % ('scalar', len(face_values),
                          ' '.join(repr(v) for v in face_values)))
        (zero / name).write_text(scalar_field(name, values, patch))

    t_patch = (inlet % ('scalar', len(T_inlet), ' '.join(repr(v) for v in T_inlet)))
    (zero / 'T').write_text(scalar_field('T', T, t_patch, dimensions='[0 0 0 1 0 0 0]'))
    u_strings = ' '.join('(%r 0 0)' % v for v in ux_inlet)
    (zero / 'U').write_text(vector_field(
        'U', [(v, 0.0, 0.0) for v in ux],
        'inlet { type fixedValue; value nonuniform List<vector> %d ( %s ); } '
        'outlet { type zeroGradient; } walls { type slip; } front { type empty; } '
        'back { type empty; }' % (len(ux_inlet), u_strings)))
    (zero / 'p').write_text(FOAMFILE.format(cls='volScalarField', obj='p') + (
        'dimensions      [1 -1 -2 0 0 0 0];\n'
        'internalField   uniform %r;\n'
        'boundaryField\n{\n'
        'inlet { type zeroGradient; } outlet { type fixedValue; value uniform %r; } '
        'walls { type zeroGradient; } front { type empty; } back { type empty; }\n}\n'
        % (cfg['pressure'], cfg['pressure'])))

    files = {}
    for path in sorted(out.rglob('*')):
        if path.is_file():
            files[str(path.relative_to(out))] = sha256(path)

    dy = H / ny
    dx = L / nx
    inlet_flux = 0.0
    inlet_ox_flux = 0.0
    for iy in range(ny):
        flux = (props['rho_fuel'] * props['u_fuel'] if is_fuel[iy]
                else props['rho_ox'] * props['u_ox']) * dy * cfg['depth']
        inlet_flux += flux
        if not is_fuel[iy]:
            inlet_ox_flux += flux

    receipt = dict(
        schema='of8-mixing-case-receipt-v1',
        case=str(out),
        source_commit=source_commit or 'unrecorded',
        purpose=('bounded 2-D two-stream cold-mixing diagnostic with exact inlet fluxes; '
                 'NOT a G2 replication'),
        frozen_inputs=copied,
        pressure_Pa=cfg['pressure'],
        mesh=dict(nx=nx, ny=ny, cells=n, dx=dx, dy=dy, depth=cfg['depth']),
        streams=dict(
            fuel=dict(name=fuel['name'], species=fuel['species'],
                      temperature_K=fuel['temperature'],
                      velocity_m_per_s=props['u_fuel']),
            oxidiser=dict(name=ox['name'], species=ox['species'],
                          temperature_K=ox['temperature'],
                          velocity_m_per_s=props['u_ox']),
            ideal_gas_density_kg_m3=dict(fuel=props['rho_fuel'], oxidiser=props['rho_ox']),
            registered_g2=dict(oxygen_mass_flow_kg_s=cfg['g2_oxygen_mass_flow'],
                               fuel_mass_flow_kg_s=cfg['g2_fuel_mass_flow'],
                               mass_flow_ratio=props['mass_flow_ratio']),
            matched_quantity=('oxidiser-to-fuel inlet mass-flux ratio equals the registered '
                              'G2 mass-flow ratio, with equal stream areas'),
        ),
        inlet_flux=dict(total_mass_flux_kg_per_s=inlet_flux,
                        oxidiser_mass_flux_kg_per_s=inlet_ox_flux,
                        fuel_mass_flux_kg_per_s=inlet_flux - inlet_ox_flux),
        boundary_conditions=dict(
            inlet='U/T/Y fixedValue (nonuniform profile), p zeroGradient',
            outlet='p fixedValue, U/T/Y zeroGradient',
            walls='slip', front_back='empty'),
        chemistry='off',
        deviations_from_registered_target=[
            'pressure 101325 Pa instead of 5.59 MPa: the frozen build is hePsiThermo+perfectGas '
            'and has no real-fluid equation of state; at 85 K and 5.59 MPa the ideal-gas density '
            'of O2 is 254 kg/m3 against a real-fluid value of about 1140 kg/m3',
            'oxidiser temperature 100 K instead of 85 K: at 101325 Pa, oxygen at 85 K is below '
            'its 90.19 K normal boiling point and is not a gas',
            'no OH or OH* observable, no mean-field or optical comparison: the registered '
            'schmitt2020-fig-18-g2 observable needs the real-fluid LES this build cannot run',
            'no reaction: GRI reactions reference species outside the 3-species subset, so the '
            'reaction list is empty and chemistry is off. This is a cold-mixing (inert) '
            'diagnostic of the inlet fluxes, mixing width and conservation, not a flame',
        ],
        controls=dict(startFrom='startTime', startTime=0.0, stopAt='endTime',
                      endTime=cfg['end_time'], deltaT=cfg['delta_t'],
                      adjustTimeStep='no', writeInterval=cfg['write_interval'],
                      expected_writes=int(round(cfg['end_time'] / cfg['write_interval'])),
                      expected_steps=int(round(cfg['end_time'] / cfg['delta_t']))),
        files=files, file_count=len(files),
        scope=('single-rank bounded mixing diagnostic; mass-flux, positivity and species '
               'closure evidence only; no G2 replication, no convergence or acceptance claim'),
    )
    receipt_path = Path(str(out) + '.receipt.json')
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(case=str(out), cells=n, inlet_flux=inlet_flux,
                          controls=receipt['controls']), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mechanism-source', type=Path, required=True)
    parser.add_argument('--source-commit', default='')
    parser.add_argument('--nx', type=int, default=DEFAULTS['nx'])
    parser.add_argument('--ny', type=int, default=DEFAULTS['ny'])
    parser.add_argument('--end-time', type=float, default=DEFAULTS['end_time'])
    parser.add_argument('--delta-t', type=float, default=DEFAULTS['delta_t'])
    parser.add_argument('--write-interval', type=float, default=DEFAULTS['write_interval'])
    args = parser.parse_args()

    cfg = dict(DEFAULTS)
    cfg.update(nx=args.nx, ny=args.ny, end_time=args.end_time, delta_t=args.delta_t,
               write_interval=args.write_interval)
    out = args.out.resolve()
    if out.exists():
        raise SystemExit('refusing to reuse existing output %s' % out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_case(out, cfg, args.mechanism_source.resolve(), args.source_commit)


if __name__ == '__main__':
    main()
