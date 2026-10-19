"""Compare the C ABI reactor with independent frozen references; no Cantera import."""
import argparse
import ctypes as c
import hashlib
import json
import math
from pathlib import Path
import time


class Properties(c.Structure):
    _fields_ = [(name, c.c_double) for name in
                ['density', 'enthalpy', 'cp', 'conductivity', 'viscosity', 'molecular_weight']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['library', 'inputs', 'reference']:
        parser.add_argument(name, type=Path)
    parser.add_argument('--stage', type=int, default=1)
    parser.add_argument('--options', default='full')
    args = parser.parse_args()
    ref = json.loads(args.reference.read_text())
    n = len(ref['species'])
    array = c.c_double*n
    pointer = c.POINTER(c.c_double)
    lib = c.CDLL(str(args.library.resolve(strict=True)))
    lib.rf_ct_create.argtypes = [c.c_char_p, c.c_int, c.c_char_p, c.c_char_p, c.c_size_t]
    lib.rf_ct_create.restype = c.c_void_p
    lib.rf_ct_destroy.argtypes = [c.c_void_p]
    lib.rf_ct_error.argtypes = [c.c_void_p]
    lib.rf_ct_error.restype = c.c_char_p
    lib.rf_ct_species_name.argtypes = [c.c_void_p, c.c_size_t, c.c_char_p, c.c_size_t]
    lib.rf_ct_advance_cp.argtypes = [c.c_void_p, c.c_double, c.c_double, pointer, c.c_size_t,
                                   c.c_double, c.c_double, c.c_double, pointer, pointer]
    lib.rf_ct_evaluate.argtypes = [c.c_void_p, c.c_double, c.c_double, pointer, c.c_size_t,
                                 c.POINTER(Properties), pointer, pointer, pointer]
    error = c.create_string_buffer(4096)
    context = lib.rf_ct_create(str(args.inputs.resolve(strict=True)).encode(), args.stage,
                               args.options.encode(), error, len(error))
    if not context:
        raise ValueError(error.value.decode())

    def check(code):
        if code:
            raise ValueError(lib.rf_ct_error(context).decode())

    def enthalpy(temperature, pressure, y):
        props, diffusion = Properties(), array()
        check(lib.rf_ct_evaluate(context, temperature, pressure, y, n, c.byref(props), None, diffusion, None))
        return props.enthalpy

    def advance(row):
        initial, final, temperature = array(*row['Y0']), array(), c.c_double()
        start = time.perf_counter()
        check(lib.rf_ct_advance_cp(context, row['T0'], row['p'], initial, n, row['duration'],
                                  ref['relative_tolerance'], ref['absolute_tolerance'],
                                  c.byref(temperature), final))
        return temperature.value, list(final), time.perf_counter()-start

    try:
        for k, name in enumerate(ref['species']):
            check(lib.rf_ct_species_name(context, k, error, len(error)))
            if error.value.decode() != name:
                raise ValueError('Species ordering mismatch')
        output = []
        for row in ref['cases']:
            h0 = enthalpy(row['T0'], row['p'], array(*row['Y0']))
            temperature, y, elapsed = advance(row)
            h = enthalpy(temperature, row['p'], array(*y))
            element_error = max(abs(math.fsum(v*(new-old) for v, new, old in zip(e, y, row['Y0'])))
                                for e in ref['element_mass_matrix'])
            item = dict(target_T=row['target_T'], duration_s=row['duration'], T=temperature,
                        maximum_Y_error=max(abs(a-b) for a, b in zip(y, row['Y'])),
                        T_error_K=abs(temperature-row['T']), sum_Y_error=abs(math.fsum(y)-1),
                        element_mass_error=element_error, minimum_Y=min(y),
                        enthalpy_error_J_kg=h-h0, wall_seconds=elapsed, Y=y)
            if item['sum_Y_error']>1e-8 or element_error>1e-8 or min(y)<-1e-9:
                raise ValueError('Species or elemental conservation failed: '+str(item))
            if abs(h-h0)>max(0.01, abs(h0)*1e-8):
                raise ValueError('Specific enthalpy conservation failed: '+str(item))
            if args.stage == 1 and (item['maximum_Y_error']>2e-8 or item['T_error_K']>1e-4):
                raise ValueError('Independent Python reactor parity failed: '+str(item))
            output.append(item)
        history_error = 0
        for row, first in zip(reversed(ref['cases']), reversed(output)):
            temperature, y, _ = advance(row)
            history_error = max(history_error, abs(temperature-first['T']),
                                max(abs(a-b) for a, b in zip(y, first['Y'])))
        if history_error>1e-7:
            raise ValueError('Reactor history leaked between states')
        # Failure must not poison a subsequent valid call.
        row = ref['cases'][-1]
        result = lib.rf_ct_advance_cp(context, row['T0'], row['p'], array(*row['Y0']), n,
                                     -1, 1e-10, 1e-18, c.byref(c.c_double()), array())
        if result == 0:
            raise ValueError('Negative integration duration accepted')
        advance(row)
        for item in output:
            del item['Y']
        print(json.dumps(dict(stage=args.stage, options=args.options, checks=output,
                              reverse_order_maximum_error=history_error,
                              library_sha256=hashlib.sha256(args.library.read_bytes()).hexdigest(),
                              reference_sha256=hashlib.sha256(args.reference.read_bytes()).hexdigest(),
                              qualification='ideal parity' if args.stage == 1 else 'conservation only'), indent=2))
    finally:
        lib.rf_ct_destroy(context)


if __name__ == '__main__':
    main()
