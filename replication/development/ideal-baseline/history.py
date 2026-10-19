"""Assess transient ideal-gas histories without promoting them to steady speeds."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'premixed-sensitivity'))
from gate import LEVELS, STAGES, load
from analyze import select, tracking


def common_endpoint(rows):
    ends = []
    for side in ('left', 'right'):
        for stage in STAGES:
            for level in [2e-5]:
                times = [float(r['time_s']) for r in rows if r['side']==side
                         and r['stage']==stage and abs(float(r['OH_level'])-level)<1e-15]
                if not times:
                    raise ValueError('Missing side/stage/marker series')
                ends.append(max(times))
    return min(ends)


def assess(rows, window=5e-6):
    end = common_endpoint(rows)
    start = end-window
    result = {'end_time_s': end, 'window_s': [start, end],
              'scientific_acceptance': False, 'status': 'TRANSIENT_UNQUALIFIED'}
    try:
        result['primary'] = {}
        for side in ('left', 'right'):
            stages = {}
            for stage in [STAGES[0]]:
                data = select(rows, stage, side, 2e-5, start, end)
                speeds = data['speed_m_s']*100
                stages[stage] = {'median_cm_s': float(np.median(speeds)),
                                 'min_cm_s': float(min(speeds)),
                                 'max_cm_s': float(max(speeds))}
            data = select(rows, STAGES[1], side, 2e-5, start, end)
            stages['tracking'] = tracking(data, side)
            stages['position_mm'] = [float(data['x_m'][0])*1000,
                                     float(data['x_m'][-1])*1000]
            stages['local_velocity_m_s'] = [float(min(data['U_local'])), float(max(data['U_local']))]
            result['primary'][side] = stages
        result['max_left_right_gap_cm_s'] = max(abs(
            result['primary']['left'][s]['median_cm_s']-
            result['primary']['right'][s]['median_cm_s']) for s in [STAGES[0]])
        result['max_temporal_range_cm_s'] = max(
            result['primary'][side][s]['max_cm_s']-result['primary'][side][s]['min_cm_s']
            for side in ('left', 'right') for s in [STAGES[0]])
        result['max_tracking_source_gap_cm_s'] = max(abs(
            result['primary'][side]['tracking']['local_density_weighted_cm_s']-
            result['primary'][side][stage]['median_cm_s'])
            for side in ('left', 'right') for stage in [STAGES[0]])
        result['tracked_left_right_gap_cm_s'] = abs(
            result['primary']['left']['tracking']['local_density_weighted_cm_s']-
            result['primary']['right']['tracking']['local_density_weighted_cm_s'])
        result['marker_checks'] = {}
        for side in ('left', 'right'):
            for level in LEVELS:
                key = side+'|'+str(level)
                try:
                    data = select(rows, STAGES[0], side, level, start, end)
                    kinematics = select(rows, STAGES[1], side, level, start, end)
                    result['marker_checks'][key] = {
                        'integrated_source_cm_s':float(np.median(data['speed_m_s']))*100,
                        'tracked_cm_s':tracking(kinematics,side)['local_density_weighted_cm_s']}
                except ValueError as exc:
                    result['marker_checks'][key] = {'unresolved_reason':str(exc)}
    except ValueError as exc:
        result['unresolved_reason'] = str(exc)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('cantera', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a new output directory')
    register = json.loads((args.snapshot/'snapshot.json').read_text())
    cantera = {round(r['phi'], 3): r['speed_cm_s'] for r in json.loads(args.cantera.read_text())}
    cases = []
    for record in register['jobs']:
        path = args.snapshot/record['job']/'flame-speed.csv'
        rows = load(path)
        cfg = json.loads((path.parent/'paper-case.json').read_text())
        raw = path.read_bytes()
        result = assess(rows)
        result.update(job=record['job'], phi=cfg['phi'], source=record['source'],
                      history_sha256=hashlib.sha256(raw).hexdigest(),
                      ignored_partial_bytes=len(raw)-(raw.rfind(b'\n')+1),
                      cantera_cm_s=cantera[round(cfg['phi'], 3)])
        cases.append((cfg['phi'], rows, result))
    cases.sort(key=lambda x:x[0])
    args.output.mkdir(parents=True)
    plt.rcParams.update({'font.family':'Arial','font.size':8,'axes.linewidth':.7,
                         'lines.linewidth':1,'legend.fontsize':8})
    fig, axes = plt.subplots(3, 4, figsize=(12, 8))
    for ax, (phi, rows, result) in zip(axes.flat, cases):
        for stage, color, label in [(STAGES[0], '#b55d13', 'OH solve source')]:
            for side, style in [('left','-'),('right','--')]:
                series = [r for r in rows if r['stage']==stage and r['side']==side
                          and abs(float(r['OH_level'])-2e-5)<1e-15]
                ax.plot([float(r['time_s'])*1e6 for r in series],
                        [float(r['speed_m_s'])*100 if r['status']=='valid' else np.nan for r in series],
                        color=color,ls=style,label=label+' '+side)
        ax.axhline(result['cantera_cm_s'], color='black',ls=':',label='Cantera steady')
        if 'primary' in result and 'left' in result['primary']:
            for side, marker in [('left','o'),('right','x')]:
                value = result['primary'][side]['tracking']['local_density_weighted_cm_s']
                ax.plot(result['end_time_s']*1e6,value,marker,color='#6c3986',ms=4,
                        label='Last 5 us tracked '+side)
        ax.axvspan(max(0,result['window_s'][0]*1e6),result['end_time_s']*1e6,color='0.5',alpha=.08)
        ax.set(title=f"phi={phi:.2f} | job {result['job']}",xlabel='Time (us)',ylabel='Speed (cm/s)')
        ax.set_xlim(0,result['end_time_s']*1e6*1.03)
        ax.set_yscale('symlog',linthresh=10)
        ax.grid(alpha=.15)
    axes.flat[-1].axis('off')
    handles, labels = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(handles,labels,loc='center',frameon=False)
    fig.suptitle('Ideal-gas OpenFOAM flames: developing histories, not steady flame speeds',fontsize=12)
    fig.text(.5,.015,'OH mass fraction = 2e-5. Species-solve source only; instantaneous-source speed excluded. Symmetric-log axes, linear within +/-10 cm/s.\n'
             'Purple symbols: independent density-weighted front tracking over the shaded 5-us window. Cantera: steady ideal-gas reference.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.055,1,.965))
    for ext in ['png','svg']:
        fig.savefig(args.output/('ideal-openfoam-histories.'+ext),dpi=180)
    plt.close(fig)
    report = {'snapshot_time':register['collected_local'],'window_s':5e-6,
              'cantera_results_sha256':hashlib.sha256(args.cantera.read_bytes()).hexdigest(),
              'source_register':register, 'cases':[r for _,_,r in cases],
              'status':'No steady OpenFOAM flame speed accepted; continuing existing runs',
              'speed_policy':'Density-weighted front tracking; species-solve source cross-check. Instantaneous-source speed excluded.'}
    (args.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    for _,_,r in cases:
        p=r.get('primary',{}).get('left',{})
        print(json.dumps({'phi':r['phi'],'time_us':r['end_time_s']*1e6,
            'cantera':r['cantera_cm_s'],'primary_left':p}))


if __name__ == '__main__':
    main()
