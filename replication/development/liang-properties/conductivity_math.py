"""Independent prescribed-volume Ely-Hanley mapping diagnostics, SI kmol units.

Equations: NBS TN 1039 DCST/ECSTX/TCOND/THERMC; see the conductivity audit.
The SRK volume is a declared hybrid input, not the original methane reference EOS.
"""
import numpy as np

R = 8314.46261815324
REFERENCES = {
    "current": dict(Tc=190.4, Vc=.0986, Zc=.288, omega=.011, W=16.04),
    "tn1039": dict(Tc=190.555, Vc=1/10.23, Zc=.283742, omega=.01131, W=16.043),
}


def srk_volumes(temperature, pressure, x, parameters, volume=None):
    tc, pc, _, _, omega, eos = parameters.T
    m = .48+1.574*omega-.176*omega**2
    si = np.sqrt(.42747*(R*tc)**2/pc)*np.abs(1+m*(1-np.sqrt(temperature/tc)))*eos
    bi = .08664*R*tc/pc*eos
    b, q = x@bi, x@si
    a = q*q
    if volume is None:
        aa, bb = a*pressure/(R*temperature)**2, b*pressure/(R*temperature)
        roots = np.roots([1., -1., aa-bb-bb*bb, -aa*bb])
        real = roots.real[np.abs(roots.imag) < 1e-8]
        volume = max(real)*R*temperature/pressure
    v = volume
    pv = -R*temperature/(v-b)**2+a*(2*v+b)/(v*(v+b))**2
    px = R*temperature*bi/(v-b)**2-2*q*si/(v*(v+b))+a*bi/(v*(v+b)**2)
    vx = -px/pv
    if not v > b or not pv < 0:
        raise ValueError("Unstable SRK root")
    partial = v+vx-x@vx
    assert abs(x@partial/v-1) < 1e-10
    return v, partial


def shape(temperature_ratio, volume_ratio, parameters, reference, lower_t):
    tc, pc, vc, _, omega, _ = parameters.T
    tr = np.minimum(2., np.maximum(lower_t, temperature_ratio))
    vr = np.clip(volume_ratio, .5, 2.)
    delta = omega-reference["omega"]
    theta = 1+delta*(.090569-.862762*np.log(tr)+(.316636-.465684/tr)*(vr-.5))
    zc = pc*vc/(R*tc)
    phi = (1+delta*(.394901*(vr-1.023545)-.932813*(vr-.754639)*np.log(tr)))*reference["Zc"]/zc
    f, h = tc/reference["Tc"]*theta, vc/reference["Vc"]*phi
    if not np.all(np.isfinite(f)) or not np.all(f > 0) or not np.all(h > 0):
        raise ValueError("Nonpositive conformal shape")
    return f, h


def mix_shapes(fi, hi, x):
    hij = (np.cbrt(hi[:, None])+np.cbrt(hi[None, :]))**3/8
    fij = np.sqrt(fi[:, None]*fi[None, :])
    xx = x[:, None]*x[None, :]
    h = np.sum(xx*hij)
    f = np.sum(xx*fij*hij)/h
    return f, h, fij, hij, xx


def mapping(temperature, volume, x, parameters, reference, mode):
    tc, _, vc, _, _, _ = parameters.T
    if mode == "partial":
        _, partial = srk_volumes(temperature, 1., x, parameters, volume=volume)
        fi, hi = shape(temperature/tc, partial/vc, parameters, reference, .5)
        f, h, *_ = mix_shapes(fi, hi, x)
        return fi, hi, f, h, 1, 0.
    if mode != "coupled":
        raise ValueError("Unknown map")
    fi, hi = tc/reference["Tc"], vc/reference["Vc"]
    active = x > 0
    for iteration in range(500):
        f, h, *_ = mix_shapes(fi, hi, x)
        fn, hn = fi.copy(), hi.copy()
        # Absent components contribute exactly zero to the mixture map. Solving
        # their hypothetical conformal state can leave the correlation's domain.
        # No positive trace concentration is truncated by this selection.
        fn[active], hn[active] = shape(
            fi[active]*temperature/(f*tc[active]), hi[active]*volume/(h*vc[active]),
            parameters[active], reference, 1e-12)
        residual = max(np.max(abs(fn/fi-1)), np.max(abs(hn/hi-1)))
        if residual < 1e-11:
            f, h, *_ = mix_shapes(fn, hn, x)
            return fn, hn, f, h, iteration+1, residual
        # Damping stabilizes the implicit component states without altering the root.
        fi, hi = .5*(fi+fn), .5*(hi+hn)
    raise ValueError("Coupled map did not converge")


def reference_viscosity(temperature):
    t = np.minimum(temperature, 10000.)
    coefficients = [2.907741307e6, -3.312874033e6, 1.608101838e6,
                    -4.331904871e5, 7.062481330e4, -7.116620750e3,
                    4.325174400e2, -1.445911210e1, .2037119479]
    return sum(c*t**((i-3.)/3.) for i, c in enumerate(coefficients))*1e-7


def reference_conductivity(density, temperature, reference):
    t, r = temperature, density
    dilute = 15*R/(4*reference["W"])*reference_viscosity(t)
    linear = (-.252762920+.334328590*(1.12-np.log(t/168.))**2)*r
    excess = np.exp(-7.197708227+85.678222640/t)*np.expm1(
        (12.471834689-984.62522975*t**-1.5)*r**.1
        +(r/.1628-1)*np.sqrt(r)*(.35946850007+69.798412538/t-872.88332851/t**2))
    return dilute+1e-3*(linear+excess)


def conductivity(temperature, volume, x, parameters, cp_r, mode="partial",
                 reference_name="current", correction=False, step=1e-5):
    ref = REFERENCES[reference_name]
    fi, hi, f, h, iterations, residual = mapping(temperature, volume, x, parameters, ref, mode)
    weights = parameters[:, 3]
    _, _, fij, hij, xx = mix_shapes(fi, hi, x)
    inverse_weight = .5*(weights[:, None]+weights[None, :])/(weights[:, None]*weights[None, :])
    mass = np.sum(xx*np.sqrt(inverse_weight*fij)*hij**(-4./3.))
    effective_weight = mass**-2*f*h**(-8./3.)
    viscosity = reference_viscosity(temperature/fi)*np.sqrt(fi*weights/ref["W"])*hi**(-2./3.)
    internal = viscosity/weights*1.32*R*np.maximum(cp_r-2.5, 0)
    denominator = internal[:, None]+internal[None, :]
    pair_internal = np.divide(2*internal[:, None]*internal[None, :], denominator,
                              out=np.zeros_like(denominator), where=denominator > 0)
    lambda_internal = np.sum(xx*pair_internal)
    reference_density = ref["W"]*h/volume*1e-3
    reference_temperature = temperature/f
    scale = np.sqrt(f*ref["W"]/effective_weight)*h**(-2./3.)
    translational = scale*reference_conductivity(reference_density, reference_temperature, ref)
    derivative = 0.
    if correction:
        dt = temperature*step
        high = mapping(temperature+dt, volume, x, parameters, ref, mode)[2]
        low = mapping(temperature-dt, volume, x, parameters, ref, mode)[2]
        derivative = (high-low)/(2*dt)
    zc = parameters[:, 1]*parameters[:, 2]/(R*parameters[:, 0])
    cort = ((1-temperature/f*min(0., derivative))*ref["Zc"]/(x@zc))**1.5 if correction else 1.
    total = lambda_internal+translational*cort
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Invalid conductivity")
    return dict(lambda_W_mK=float(total), internal_W_mK=float(lambda_internal),
                translational_W_mK=float(translational), CORT=float(cort),
                f=float(f), h=float(h), df_dT_fixed_v=float(derivative),
                T0_K=float(reference_temperature), rho0_g_cm3=float(reference_density),
                effective_W=float(effective_weight), iterations=iterations,
                mapping_residual=float(residual))
