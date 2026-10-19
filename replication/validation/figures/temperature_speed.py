"""Adapt DeepFlame's temperature-front concept to actual saved times and upstream U."""
import json
from pathlib import Path
import sys
import numpy as np

snapshot, output = (Path(v).resolve() for v in sys.argv[1:3])
data = json.loads(snapshot.read_text(encoding='utf-8-sig'))
results = []
for job in data['jobs']:
    cfg = job['metadata']['config']; n = cfg['cells']; dx = cfg['length_m']/n
    x = (np.arange(n)+.5)*dx
    history = []
    for sample in job['samples']:
        fields = sample['fields']; gradient = np.gradient(fields['T'], x)
        peak = int(np.argmax(gradient)); assert 0 < peak < n-1
        offset = .5*(gradient[peak-1]-gradient[peak+1])/(gradient[peak-1]-2*gradient[peak]+gradient[peak+1])
        assert abs(offset) <= 1
        # The first 100 cells are cold and away from the flame in this benchmark.
        assert max(fields['T'][:100]) < cfg['unburned_temperature_K']+1
        history.append([sample['time_s'], x[peak]+offset*dx, float(np.mean(fields['U'][:100]))])
    rows = np.array(history)
    result = {'job': job['job'], 'method': 'maximum positive dT/dx, three-point parabolic interpolation; measured fresh-gas U minus fitted front velocity',
              'qualification': 'Adapted DeepFlame concept; not direct Eq40 or established steady travelling-wave speed', 'history': history}
    for count, label in [(6, '50us'), (11, '100us')]:
        window = rows[-count:]; assert np.allclose(np.diff(window[:,0]),1e-5)
        velocity = np.polyfit(window[:,0]-window[0,0], window[:,1], 1)[0]
        result[label] = {'start_s': float(window[0,0]), 'end_s': float(window[-1,0]),
                         'speed_cm_s': float(100*(window[:,2].mean()-velocity))}
    results.append(result)
output.write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps([{k:v for k,v in r.items() if k!='history'} for r in results], indent=2))
