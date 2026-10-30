"""Measured conservation and coordinate extrema; no scientific acceptance."""
import numpy as np


def analyse(rows, settings, initial, cmax):
    time = np.array([row['time_s'] for row in rows])
    hscale = max(abs(initial['h_J_kg']), abs(initial['CpT_J_kg']), 1)
    metrics = {
        'enthalpy_scaled': max(abs(row['h_J_kg']-initial['h_J_kg'])/hscale for row in rows),
        'mass_relative': max(abs(row['mass_kg']/initial['mass_kg']-1) for row in rows),
        'pressure_relative': max(abs(row['p_Pa']/initial['p_Pa']-1) for row in rows),
        'element_absolute': max(abs(row[key]-initial[key]) for row in rows for key in initial if key.startswith('element_')),
        'negative_species_absolute': max(0, -min(row['minimum_Y'] for row in rows)),
    }
    coordinates = {}
    tolerance = settings['progress_significance_absolute']
    for name, source in [('C','Sc_kg_m3_s'), ('Cwater','Scwater_kg_m3_s')]:
        values = np.array([row[name] for row in rows])
        rate = np.array([row[source] for row in rows])
        peak, low = int(values.argmax()), int(values.argmin())
        drop = float(np.max(np.maximum.accumulate(values)-values))
        rise = float(np.max(values-np.minimum.accumulate(values)))
        coordinates[name] = {'initial':float(values[0]),'final':float(values[-1]),
            'minimum':float(values[low]),'maximum':float(values[peak]),
            'time_of_maximum_s':float(time[peak]),'maximum_reversal_from_prior_peak':drop,
            'maximum_increase_from_prior_low':rise,'nondecreasing_within_tolerance':drop<=tolerance,
            'nonincreasing_within_tolerance':rise<=tolerance,
            'increases_then_reverses':bool(values[peak]-values[0]>tolerance and values[peak]-values[peak:].min()>tolerance),
            'initial_full_source_kg_m3_s':float(rate[0]),'minimum_source_kg_m3_s':float(rate.min()),
            'maximum_source_kg_m3_s':float(rate.max())}
    coordinates['C']['maximum_excess_over_initial_table_Cmax'] = coordinates['C']['maximum']-cmax
    return {'records':len(rows),'actual_final_time_s':float(time[-1]),
            'requested_time_covered':bool(time[-1]>=settings['end_time_s']*(1-1e-12)),
            'conservation':metrics,'conservation_limits':settings['limits'],
            'conservation_passed':all(metrics[key]<=value for key,value in settings['limits'].items()),
            'progress_significance_absolute':tolerance,'coordinates':coordinates,
            'maximum_temperature_K':max(row['T_K'] for row in rows),
            'minimum_temperature_K':min(row['T_K'] for row in rows),
            'scientific_acceptance':False}
