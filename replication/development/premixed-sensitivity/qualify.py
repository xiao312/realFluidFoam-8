"""Read completed segments and write qualification only inside this new job."""
import json
from pathlib import Path
import sys
from check import check
from gate import evaluate, load

JOBS = {'dt100': '124873143', 'dt50': '124873144', 'dt25': '124873146'}


def qualify(output):
    output = output.resolve()
    if output.parent != Path('/work/jobs'):
        raise ValueError('Expected contained qualification job')
    results = {}
    for key, identifier in JOBS.items():
        donor = output.parent/identifier
        try:
            operational = check(donor)
            diagnostic = evaluate(load(donor/'case/processor0/flame-speed.csv'))
            results[key] = {'job': identifier, 'operational': operational,
                            'diagnostic': diagnostic, 'operational_pass': True}
        except (ValueError, OSError) as error:
            results[key] = {'job': identifier, 'operational_pass': False, 'error': str(error)}
    (output/'qualification.json').write_text(json.dumps(results, indent=2))
    passed = all(r['operational_pass'] for r in results.values())
    (output/'result.txt').write_text(('PASS' if passed else 'FAIL') +
        ': segment operational checks; scientific gates remain separate\n')
    print(json.dumps(results, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(qualify(Path(sys.argv[1])))
