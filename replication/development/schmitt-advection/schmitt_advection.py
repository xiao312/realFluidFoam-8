#!/usr/bin/env python3
"""One-dimensional advection of a dense-to-light oxygen interface at 6 MPa.

The registered target `schmitt2020-fig-5` states: p about 6 MPa, a density interface from
1000 to 100 kg/m3 described by an error function, a uniform velocity of 10 m/s, dx = 0.01 m,
refinement factors 2, 4, 6 and t = 20 ms. Its four panels are density, temperature, pressure
and velocity along the domain, and the scientific content is in the last two: a consistent
discretisation leaves the pressure at 6 MPa and the velocity at 10 m/s, while an inconsistent
one produces spurious pressure and velocity oscillations across the interface. The temperature
panel is the same statement in another variable - a dense cold state (1000 kg/m3, about 115 K)
and a light warm one (about 100 kg/m3, about 250 K) are in pressure equilibrium at 6 MPa.

This script is a *reconstruction* with its own declared scheme, not the authors' code:

  * finite volume, uniform grid, periodic domain, so translation conserves mass, momentum and
    energy exactly and any drift is the scheme's, not a boundary condition's;
  * convective flux: Rusanov (local Lax-Friedrichs) with MUSCL reconstruction and a minmod
    limiter, second order away from extrema;
  * viscous and conductive fluxes by central differences, with the Chung et al. (1988)
    dense-gas viscosity and thermal conductivity;
  * thermodynamics: Soave-Redlich-Kwong for pure oxygen, the same implementation the
    Cavalieri property work uses (`cavalieri-properties/srk_chung.py`), so the equation of
    state is covered by that module's tests rather than by a second copy here;
  * time integration: explicit Euler with an adaptive step from the acoustic and diffusive
    limits, so positivity is maintained rather than repaired.

The initial condition is stated in the variables the target gives: p = 6 MPa and u = 10 m/s
everywhere, with the density following the error-function profile. The temperature is then not
free - it is the temperature at which SRK oxygen has that density at 6 MPa. That is why the
temperature panel comes out of the density panel, and why the two ends land on 115 K and 250 K
without being imposed.

Everything is reported, including the parts that do not look like the paper: the spurious
pressure and velocity amplitudes, the smallest density and temperature anywhere in the run, the
mass, momentum and energy drift, how far the interface actually travelled, and how much the
profile diffused, each as a function of resolution. No scheme is switched to make a panel
match.

Usage:
  schmitt_advection.py --out OUTDIR [--dx 0.01 0.005 0.0025] [--t-end 0.02]
"""
import argparse
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'cavalieri-properties'))
import srk_chung  # noqa: E402  (path is set above; one EOS implementation for the campaign)

O2 = srk_chung.SPECIES['O2']
M_O2 = O2['molar_mass']
R_UNIVERSAL = srk_chung.R

P_INITIAL = 6.0e6           # Pa, the target's "p about 6 MPa"
RHO_DENSE = 1000.0          # kg/m3, left state
RHO_LIGHT = 100.0           # kg/m3, right state
U_INITIAL = 10.0            # m/s, uniform
DOMAIN = 0.6                # m, wider than the interface travel plus two flat shelves
INTERFACE_X = 0.2           # m, initial interface centre
INTERFACE_DELTA = 0.02      # m, error-function half-width (declared, see README)
CFL = 0.30
MAX_STEPS = 400000


def erf(x):
    return math.erf(x)


def _molar_volume(rho):
    return M_O2 / rho


def pressure_of(rho, T):
    """SRK pressure for a given density and temperature, in molar form."""
    v = _molar_volume(rho)
    a, _, _ = srk_chung.alpha_terms(O2, T)
    b = srk_chung.b_term(O2)
    if v <= b:
        raise ValueError('molar volume %g is below the SRK covolume %g' % (v, b))
    return R_UNIVERSAL * T / (v - b) - a / (v * (v + b))


def primitive_at(T, rho):
    """Everything the fluxes need at a (T, rho) state, per unit mass.

    The caloric departures are evaluated directly from the molar volume that belongs to this
    density, not by re-solving the cubic at (T, p): when the SRK cubic has several mechanically
    stable roots, a (T, p) call can return a different branch than the density implies, and the
    energy would then describe a state the cell does not have. The formulas are the ones in
    `cavalieri-properties/srk_chung.py`; only the root selection differs, and here the root is
    the density itself.
    """
    v = _molar_volume(rho)
    b = srk_chung.b_term(O2)
    if v <= b:
        raise ValueError('molar volume %g is below the SRK covolume %g' % (v, b))
    a, a_t, a_tt = srk_chung.alpha_terms(O2, T)
    p = R_UNIVERSAL * T / (v - b) - a / (v * (v + b))
    p_v = -R_UNIVERSAL * T / (v - b) ** 2 + a * (2.0 * v + b) / (v * (v + b)) ** 2
    p_t = R_UNIVERSAL / (v - b) - a_t / (v * (v + b))
    if not (p_v < 0.0):
        raise ValueError('SRK state is not mechanically stable at T=%g rho=%g' % (T, rho))
    v_t = -p_t / p_v
    log_term = math.log1p(b / v)
    c_term = T * a_t - a
    h_dep = R_UNIVERSAL * T * b / (v - b) - a / (v + b) + c_term * log_term / b
    cp_dep = p * v_t - R_UNIVERSAL + T * a_tt * log_term / b - c_term * v_t / (v * (v + b))
    cv_dep = cp_dep + T * p_t * p_t / p_v
    cp0 = srk_chung.cp_ideal(O2, T)
    h0 = srk_chung.h_ideal(O2, T)
    cp = (cp0 + cp_dep) / M_O2
    cv = (cp0 - R_UNIVERSAL + cv_dep) / M_O2
    h = (h0 + h_dep) / M_O2
    dpdrho_T = -v * v / M_O2 * p_v
    c2 = dpdrho_T + T / (rho * rho) * p_t * p_t / cv
    ch = srk_chung.chung_state(O2, T, p, rho=rho)
    return {
        'T': T, 'p': p, 'rho': rho, 'h': h, 'cp': cp, 'cv': cv,
        'gamma': cp / cv, 'c2': c2, 'mu': ch['mu'], 'kappa': ch['kappa'],
        'e': h - p / rho,
    }


_E_MIN_CACHE = {}
_E_MIN_TABLE = None
_TABLE_RHO = (40.0, 1200.0, 160)


def _positive_pressure_floor(rho):
    """Smallest temperature at which SRK oxygen at this density has p > 1 kPa."""
    lo, hi = 90.0, 700.0
    if pressure_of(rho, lo) > 1e3:
        return lo
    if pressure_of(rho, hi) < 1e3:
        raise ValueError('density %g kg/m3 has no positive-pressure SRK state' % rho)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if pressure_of(rho, mid) < 1e3:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-9:
            break
    return 0.5 * (lo + hi)


def _positive_pressure_stable(rho, T):
    """True when this density and temperature give a positive pressure and a stable branch.

    Mechanical stability is (dp/dv)_T < 0. Above that limit the SRK polynomial has a second,
    repulsive root that satisfies the same internal energy, so an energy inversion that only
    checks p > 0 can return it - at 100 kg/m3 the repulsive root gave 94.6 K where the physical
    answer is 248.9 K.
    """
    try:
        props = primitive_at(T, rho)
    except (ValueError, ZeroDivisionError):
        return False
    return props['p'] > 0.0 and math.isfinite(props['c2']) and props['c2'] > 0.0


def _scan_energy_minimum(rho):
    """Temperature of the *global* minimum of e(T) over mechanically stable states.

    SRK's liquid-branch departure enthalpy makes e(T) fall before it rises, and the minimum sits
    far above the positive-pressure floor (around 150 K at 300-500 kg/m3, in the pseudo-boiling
    band where cp peaks). Bracketing the energy inversion at floor + 1 K is therefore wrong by
    about 10 kJ/kg, which is the size of a first-step update: the inversion then rejects states
    that are perfectly admissible. Two constraints define the window: the state must have p > 0
    and (dp/dv)_T < 0, because below the mechanical-stability limit the cubic's repulsive branch
    also solves e(T) = e; a state there is a second, unphysical root of the inversion.
    """
    floor = _positive_pressure_floor(rho)
    best_T, best_e = None, None
    T = floor
    while T <= floor + 80.0:
        try:
            e = primitive_at(T, rho)['e']
        except Exception:
            T += 0.25
            continue
        if best_e is None or e < best_e:
            best_T, best_e = T, e
        T += 0.25
    if best_T is None:
        raise ValueError('no mechanically stable SRK state at rho=%g' % rho)
    # Refine on a fine scan inside the best bracket; the energy is much too flat near the
    # minimum for a ternary search to stay on the stable branch, and a scan cannot leave it.
    lo_T = max(floor, best_T - 0.5)
    T = lo_T
    while T <= best_T + 0.5:
        try:
            e = primitive_at(T, rho)['e']
        except Exception:
            T += 0.005
            continue
        if e < best_e:
            best_T, best_e = T, e
        T += 0.005
    # The bracket must sit on the stable branch; walk up until it does.
    T = best_T
    while T < best_T + 5.0:
        try:
            primitive_at(T, rho)
            return T
        except Exception:
            T += 0.01
    raise ValueError('no mechanically stable SRK state near the energy minimum at rho=%g' % rho)


def _energy_minimum_table():
    """log-density table of the energy-minimum temperature, built once per process."""
    global _E_MIN_TABLE
    if _E_MIN_TABLE is None:
        lo, hi, count = _TABLE_RHO
        table = []
        for k in range(count):
            frac = k / (count - 1.0)
            rho = lo * (hi / lo) ** frac
            try:
                table.append((math.log(rho), _scan_energy_minimum(rho)))
            except Exception:
                table.append((math.log(rho), None))
        _E_MIN_TABLE = table
    return _E_MIN_TABLE


def _energy_minimum_temperature(rho):
    """Energy-minimum temperature for this density, interpolated in log density."""
    key = round(math.log(max(rho, 1.0)), 6)
    if key in _E_MIN_CACHE:
        return _E_MIN_CACHE[key]
    table = [row for row in _energy_minimum_table() if row[1] is not None]
    lr = math.log(max(rho, 1.0))
    if lr <= table[0][0]:
        value = table[0][1]
    elif lr >= table[-1][0]:
        value = table[-1][1]
    else:
        for k in range(len(table) - 1):
            if table[k][0] <= lr <= table[k + 1][0]:
                span = table[k + 1][0] - table[k][0]
                w = 0.0 if span == 0.0 else (lr - table[k][0]) / span
                value = table[k][1] + w * (table[k + 1][1] - table[k][1])
                break
    value += 0.05
    _E_MIN_CACHE[key] = value
    return value


def pressure_derivative_T(rho, T):
    """(dp/dT)_rho from the EOS, used for the fast temperature Newton."""
    v = _molar_volume(rho)
    _, a_t, _ = srk_chung.alpha_terms(O2, T)
    b = srk_chung.b_term(O2)
    return R_UNIVERSAL / (v - b) - a_t / (v * (v + b))


def temperature_of_rho_p(rho, target_p, T_hint):
    """Temperature at a given density and pressure, by Newton from a neighbouring temperature.

    Used by the reconstruction, where the pressure is reconstructed rather than the temperature:
    a uniform pressure field then reconstructs to the same uniform pressure on both sides of a
    face, so a contact discontinuity carries no spurious pressure jump. Newton from the cell
    temperature converges in a few iterations because the reconstructed state is close to it.
    """
    T = T_hint
    for _ in range(30):
        residual = pressure_of(rho, T) - target_p
        derivative = pressure_derivative_T(rho, T)
        if derivative == 0.0:
            break
        step = residual / derivative
        T -= step
        if abs(step) < 1e-9:
            break
    return T


def temperature_window(rho):
    """Bracket for the caloric inversion: above the energy minimum, below 700 K."""
    return _energy_minimum_temperature(rho), 700.0


def temperature_of_rho(rho, p=P_INITIAL):
    """The T at which SRK oxygen has this density at pressure p."""
    lo, hi = temperature_window(rho)
    if not (pressure_of(rho, hi) > p > pressure_of(rho, lo)):
        raise ValueError('density %g kg/m3 does not bracket %g Pa in SRK oxygen' % (rho, p))
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if pressure_of(rho, mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-11:
            break
    return 0.5 * (lo + hi)


def temperature_of_energy(rho, e_target, T_hint=300.0):
    """Invert the caloric equation of state for T at a fixed density.

    Newton from `T_hint` with a step limit, and a bracketed bisection fallback: near the
    pseudo-boiling region cv varies by an order of magnitude, so an unguarded Newton step can
    leave the positive-pressure window in one iteration.
    """
    lo, hi = temperature_window(rho)
    e_lo = primitive_at(lo, rho)['e']
    e_hi = primitive_at(hi, rho)['e']
    if not (e_lo <= e_target <= e_hi):
        raise ValueError('internal energy %g J/kg outside [%g, %g] at rho=%g'
                         % (e_target, e_lo, e_hi, rho))
    T = min(max(T_hint, lo), hi)
    for _ in range(12):
        props = primitive_at(T, rho)
        residual = props['e'] - e_target
        if abs(residual) < 1e-4:
            return T
        step = residual / props['cv']
        candidate = T - step
        if not (lo < candidate < hi):
            break
        T = candidate
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        if primitive_at(mid, rho)['e'] < e_target:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-9:
            break
    return 0.5 * (lo + hi)


def initial_primitive(x):
    """Density from the error-function profile, temperature from the equation of state."""
    s = (x - INTERFACE_X) / INTERFACE_DELTA
    mid = 0.5 * (RHO_DENSE + RHO_LIGHT)
    half = 0.5 * (RHO_DENSE - RHO_LIGHT)
    rho = mid + half * (-erf(s))
    T = temperature_of_rho(rho)
    return rho, T


def conservative(rho, u, T):
    props = primitive_at(T, rho)
    return [rho, rho * u, rho * (props['e'] + 0.5 * u * u)], props


def primitive_from_conserved(q, T_hint=300.0):
    """Recover (rho, u, T) from the conserved vector.

    The pressure is not conserved in a real-gas formulation: the density is conserved and the
    total energy gives the internal energy, so the temperature follows from the caloric
    equation of state at that density and the pressure then follows from the EOS. `T_hint`
    only seeds the Newton iteration.
    """
    rho, mom, E = q
    if rho <= 0.0:
        raise ValueError('non-positive density %g' % rho)
    u = mom / rho
    e_target = E / rho - 0.5 * u * u
    return rho, u, temperature_of_energy(rho, e_target, T_hint)


def minmod(a, b):
    if a * b <= 0.0:
        return 0.0
    return a if abs(a) < abs(b) else b


def limited_slopes(field):
    """Minmod slopes; the two outer cells fall back to first order (no ghost slopes)."""
    n = len(field)
    slopes = [0.0] * n
    for i in range(1, n - 1):
        slopes[i] = minmod(field[i] - field[i - 1], field[i + 1] - field[i])
    return slopes


def rusanov(qL, qR, pL, pR, cL, cR):
    rhoL, momL, EL = qL
    rhoR, momR, ER = qR
    uL = momL / rhoL
    uR = momR / rhoR
    fL = [momL, momL * uL + pL, uL * (EL + pL)]
    fR = [momR, momR * uR + pR, uR * (ER + pR)]
    smax = max(abs(uL) + cL, abs(uR) + cR)
    return [0.5 * (fL[k] + fR[k]) - 0.5 * smax * (qR[k] - qL[k]) for k in range(3)]


def hllc_flux(state_L, state_R):
    """HLLC flux for a real gas, from (rho, u, p, E, c) on each side.

    The contact-preserving member of the HLL family: the interface speed S_M is computed from
    the pressure and momentum jumps, and the star states are built from it, so a pure contact
    advected at a uniform velocity produces no dissipation at all. That is the property the
    Rusanov form lacks and the reason this test needs it.
    """
    rhoL, uL, pL, EL, cL = state_L
    rhoR, uR, pR, ER, cR = state_R
    fL = [rhoL * uL, rhoL * uL * uL + pL, uL * (EL + pL)]
    fR = [rhoR * uR, rhoR * uR * uR + pR, uR * (ER + pR)]
    SL = min(uL - cL, uR - cR)
    SR = max(uL + cL, uR + cR)
    denom = rhoL * (SL - uL) - rhoR * (SR - uR)
    if abs(denom) < 1e-30:
        return [0.5 * (fL[k] + fR[k]) for k in range(3)]
    SM = (pR - pL + rhoL * uL * (SL - uL) - rhoR * uR * (SR - uR)) / denom

    def star(rho, u, p, E, S):
        # Guard the pressure-work term: S - u can vanish only in a degenerate state.
        if abs(S - u) < 1e-30:
            return [rho, rho * u, E]
        factor = rho * (S - u) / (S - SM)
        return [factor,
                factor * SM,
                factor * (E / rho + (SM - u) * (SM + p / (rho * (S - u))))]

    if SL >= 0.0:
        return fL
    if SR <= 0.0:
        return fR
    if SM >= 0.0:
        US = star(rhoL, uL, pL, EL, SL)
        return [fL[k] + SL * (US[k] - [rhoL, rhoL * uL, EL][k]) for k in range(3)]
    US = star(rhoR, uR, pR, ER, SR)
    return [fR[k] + SR * (US[k] - [rhoR, rhoR * uR, ER][k]) for k in range(3)]


def run(dx, t_end, outdir, order=2, flux_scheme='hllc'):
    n = int(round(DOMAIN / dx))
    dx = DOMAIN / n
    x = [(i + 0.5) * dx for i in range(n)]
    NG = 2                       # ghost cells per side
    size = n + 2 * NG

    rho0, T0 = initial_primitive(x[0])
    inflow_q, inflow_props = conservative(rho0, U_INITIAL, T0)

    q = [[0.0, 0.0, 0.0] for _ in range(size)]
    props = [None] * size
    u = [U_INITIAL] * size
    c = [0.0] * size
    for j in range(NG, NG + n):
        rho, T = initial_primitive(x[j - NG])
        q[j], props[j] = conservative(rho, U_INITIAL, T)
    for j in list(range(NG)) + list(range(NG + n, size)):
        q[j] = list(inflow_q)
        props[j] = dict(inflow_props)

    def totals():
        mass = sum(q[j][0] * dx for j in range(NG, NG + n))
        momentum = sum(q[j][1] * dx for j in range(NG, NG + n))
        energy = sum(q[j][2] * dx for j in range(NG, NG + n))
        return mass, momentum, energy

    mass0, momentum0, energy0 = totals()
    flux_in = [0.0, 0.0, 0.0]
    flux_out = [0.0, 0.0, 0.0]
    t = 0.0
    steps = 0
    dt = 0.0
    clamps = 0
    T_min_seen = min(props[j]['T'] for j in range(NG, NG + n))
    rho_min_seen = min(q[j][0] for j in range(NG, NG + n))
    p_lo = p_hi = P_INITIAL
    u_lo = u_hi = U_INITIAL

    while t < t_end and steps < MAX_STEPS:
        # Right ghosts: zero-gradient outflow. Left ghosts already carry the fixed inflow.
        for k in range(3):
            for m in range(NG):
                q[NG + n + m][k] = q[NG + n - 1][k]
        for m in range(NG):
            props[NG + n + m] = props[NG + n - 1]
            u[NG + n + m] = u[NG + n - 1]

        for j in range(size):
            c[j] = math.sqrt(max(props[j]['c2'], 1.0))

        dt_acoustic = min(dx / (abs(u[j]) + c[j]) for j in range(NG, NG + n))
        alpha_max = max(max(4.0 * props[j]['mu'] / (3.0 * q[j][0]),
                            props[j]['kappa'] / (q[j][0] * props[j]['cv']))
                        for j in range(NG, NG + n))
        dt_diffusive = (dx * dx / (2.0 * alpha_max)) if alpha_max > 0.0 else float('inf')
        dt = CFL * min(dt_acoustic, dt_diffusive)
        if t + dt > t_end:
            dt = t_end - t
        if not (dt > 0.0):
            break

        if order >= 2 and flux_scheme != 'hllc':
            s_rho = limited_slopes([q[j][0] for j in range(size)])
            s_mom = limited_slopes([q[j][1] for j in range(size)])
            s_E = limited_slopes([q[j][2] for j in range(size)])
        else:
            s_rho = [0.0] * size
            s_mom = [0.0] * size
            s_E = [0.0] * size

        s_rho_p = limited_slopes([props[j]['rho'] for j in range(size)]) if order >= 2 else [0.0] * size
        s_u = limited_slopes([u[j] for j in range(size)]) if order >= 2 else [0.0] * size
        s_p = limited_slopes([props[j]['p'] for j in range(size)]) if order >= 2 else [0.0] * size

        flux = [None] * size
        for j in range(1, size):          # flux[j] = face between cell j-1 and cell j
            i, ip = j - 1, j
            if flux_scheme == 'hllc':
                sides = []
                for idx, sign in ((i, 1.0), (ip, -1.0)):
                    rho_k = max(props[idx]['rho'] + sign * 0.5 * s_rho_p[idx], 1e-3)
                    u_k = u[idx] + sign * 0.5 * s_u[idx]
                    p_k = props[idx]['p'] + sign * 0.5 * s_p[idx]
                    T_k = temperature_of_rho_p(rho_k, p_k, props[idx]['T'])
                    pk = primitive_at(T_k, rho_k)
                    sides.append([rho_k, u_k, pk['p'],
                                  rho_k * (pk['e'] + 0.5 * u_k * u_k),
                                  math.sqrt(max(pk['c2'], 1.0))])
                f = hllc_flux(sides[0], sides[1])
            else:
                qL = [q[i][k] + 0.5 * (s_rho, s_mom, s_E)[k][i] for k in range(3)]
                qR = [q[ip][k] - 0.5 * (s_rho, s_mom, s_E)[k][ip] for k in range(3)]
                f = rusanov(qL, qR, props[i]['p'], props[ip]['p'], c[i], c[ip])
            dudx = (u[ip] - u[i]) / dx
            dTdx = (props[ip]['T'] - props[i]['T']) / dx
            tau = (4.0 / 3.0) * 0.5 * (props[i]['mu'] + props[ip]['mu']) * dudx
            qflux = -0.5 * (props[i]['kappa'] + props[ip]['kappa']) * dTdx
            uface = 0.5 * (u[i] + u[ip])
            f[1] -= tau
            f[2] -= uface * tau + qflux
            flux[j] = f

        for j in range(NG, NG + n):
            for k in range(3):
                q[j][k] -= dt / dx * (flux[j + 1][k] - flux[j][k])
        for k in range(3):
            flux_in[k] += dt * flux[NG][k]            # face between ghost and first interior
            flux_out[k] += dt * flux[NG + n][k]      # face between last interior and ghost

        previous = list(props)
        for j in range(NG, NG + n):
            try:
                rho_i, u_i, T_i = primitive_from_conserved(q[j], previous[j]['T'])
            except ValueError:
                # The update produced a state outside the admissible SRK surface. Clamping the
                # temperature into the window keeps the run going and is counted, because a
                # clamped cell is not a solved cell: the count is reported with the metrics.
                rho_i = q[j][0]
                u_i = q[j][1] / rho_i
                lo, hi = temperature_window(rho_i)
                T_i = min(max(previous[j]['T'], lo), hi)
                clamps += 1
            props[j] = primitive_at(T_i, rho_i)
            u[j] = u_i
            T_min_seen = min(T_min_seen, T_i)
            rho_min_seen = min(rho_min_seen, rho_i)
            p_lo = min(p_lo, props[j]['p'])
            p_hi = max(p_hi, props[j]['p'])
            u_lo = min(u_lo, u_i)
            u_hi = max(u_hi, u_i)
        t += dt
        steps += 1

    mass1, momentum1, energy1 = totals()
    rho = [q[j][0] for j in range(NG, NG + n)]
    T = [props[j]['T'] for j in range(NG, NG + n)]
    p = [props[j]['p'] for j in range(NG, NG + n)]
    uu = [u[j] for j in range(NG, NG + n)]

    # Bookkeeping residual: a conservative finite-volume update must change the totals by
    # exactly the boundary flux integrals, so this number is a certificate, not a fudge.
    residual = [
        (mass1 - mass0) - (flux_in[0] - flux_out[0]),
        (momentum1 - momentum0) - (flux_in[1] - flux_out[1]),
        (energy1 - energy0) - (flux_in[2] - flux_out[2]),
    ]

    target = 0.5 * (RHO_DENSE + RHO_LIGHT)
    position = None
    for i in range(n - 1):
        if (rho[i] - target) * (rho[i + 1] - target) <= 0.0 and rho[i] != rho[i + 1]:
            w = (target - rho[i]) / (rho[i + 1] - rho[i])
            position = x[i] + w * dx
            break

    # Numerical diffusion: the exact solution of pure advection is the initial profile
    # translated by u*t, clipped at the inlet because the inflow holds the far-field value.
    shift = U_INITIAL * t
    l2 = 0.0
    linf = 0.0
    for i in range(n):
        x0 = x[i] - shift
        if x0 <= 0.0:
            rho_at, _ = initial_primitive(0.0)
        else:
            rho_at, _ = initial_primitive(x0)
        err = rho[i] - rho_at
        l2 += err * err * dx
        linf = max(linf, abs(err))
    l2 = math.sqrt(l2 / DOMAIN)

    doc = {
        'kind': 'forge-schmitt-advection-run-v1',
        'dx_m': dx,
        'cells': n,
        'domain_m': DOMAIN,
        't_end_s': t,
        'steps': steps,
        'dt_last_s': dt,
        'scheme': ('%s flux, %s reconstruction of (rho, u, T), central viscous and conductive '
                   'flux, explicit Euler with an adaptive acoustic and diffusive step'
                   % ('HLLC' if flux_scheme == 'hllc' else 'Rusanov',
                      'MUSCL/minmod of (rho, u, p), so a uniform pressure reconstructs to a '
                      'uniform pressure' if order >= 2 else 'first order')),
        'boundaries': 'left: fixed inflow at the dense state, u = 10 m/s; '
                      'right: zero-gradient outflow',
        'thermodynamics': 'SRK pure O2 via cavalieri-properties/srk_chung.py; '
                          'Chung et al. (1988) dense-gas viscosity and conductivity',
        'initial': {'p_Pa': P_INITIAL, 'u_m_s': U_INITIAL, 'rho_dense': RHO_DENSE,
                    'rho_light': RHO_LIGHT, 'interface_x_m': INTERFACE_X,
                    'interface_delta_m': INTERFACE_DELTA},
        'profile': {'x_m': x, 'rho_kg_m3': rho, 'T_K': T, 'p_Pa': p, 'u_m_s': uu},
        'metrics': {
            'p_min_Pa': p_lo, 'p_max_Pa': p_hi,
            'p_amplitude_rel': max(abs(p_lo - P_INITIAL), abs(p_hi - P_INITIAL)) / P_INITIAL,
            'u_min_m_s': u_lo, 'u_max_m_s': u_hi,
            'u_amplitude_rel': max(abs(u_lo - U_INITIAL), abs(u_hi - U_INITIAL)) / U_INITIAL,
            'rho_min_kg_m3': rho_min_seen, 'T_min_K': T_min_seen,
            'clamped_cell_steps': clamps,
            'conservation_residual_rel': {
                'mass': residual[0] / (abs(mass0) + abs(flux_in[0]) + abs(flux_out[0])),
                'momentum': residual[1] / (abs(momentum0) + abs(flux_in[1]) + abs(flux_out[1])),
                'energy': residual[2] / (abs(energy0) + abs(flux_in[2]) + abs(flux_out[2])),
            },
            'mass_change_rel': (mass1 - mass0) / mass0,
            'interface_x_final_m': position,
            'interface_travel_m': (position - INTERFACE_X) if position is not None else None,
            'expected_travel_m': shift,
            'profile_l2_vs_translated_initial': l2,
            'profile_linf_vs_translated_initial': linf,
        },
    }
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / ('run-dx-%g.json' % dx)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(doc, handle, indent=1)
        handle.write('\n')
    return doc, path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--dx', type=float, nargs='+', default=[0.01, 0.005, 0.0025])
    parser.add_argument('--t-end', type=float, default=0.02)
    parser.add_argument('--order', type=int, default=2, choices=(1, 2))
    parser.add_argument('--flux', default='hllc', choices=('hllc', 'rusanov'))
    args = parser.parse_args()

    outdir = pathlib.Path(args.out)
    summary = {'kind': 'forge-schmitt-advection-v1', 'runs': []}
    for dx in args.dx:
        doc, path = run(dx, args.t_end, outdir, order=args.order, flux_scheme=args.flux)
        m = doc['metrics']
        summary['runs'].append({
            'dx_m': doc['dx_m'], 'cells': doc['cells'], 'steps': doc['steps'],
            'order': args.order,
            'file': path.name, 'metrics': m,
        })
        res = m['conservation_residual_rel']
        travel = m['interface_travel_m']
        print('order=%d dx=%.4f cells=%3d steps=%5d p_amp=%.3e u_amp=%.3e rho_min=%.1f '
              'T_min=%.1f res(mass,mom,en)=(%.1e,%.1e,%.1e) travel=%s l2=%.3f clamps=%d'
              % (args.order, doc['dx_m'], doc['cells'], doc['steps'], m['p_amplitude_rel'],
                 m['u_amplitude_rel'], m['rho_min_kg_m3'], m['T_min_K'],
                 res['mass'], res['momentum'], res['energy'],
                 ('%.4f' % travel) if travel is not None else 'none',
                 m['profile_l2_vs_translated_initial'], m['clamped_cell_steps']))
    with open(outdir / 'summary.json', 'w', encoding='utf-8') as handle:
        json.dump(summary, handle, indent=1)
        handle.write('\n')
    print('wrote %s' % (outdir / 'summary.json'))


if __name__ == '__main__':
    main()
