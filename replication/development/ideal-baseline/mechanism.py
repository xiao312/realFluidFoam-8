"""Read the bounded author OF dictionary subset; preserve SI/kmol rate units."""
from collections import Counter
import hashlib
from pathlib import Path
import re

INPUTS = Path(__file__).resolve().parents[2]/'validation/inputs'


def block(text, name):
    match = re.search(r'(?m)^\s*'+re.escape(name)+r'\s*\{', text)
    if not match:
        raise ValueError('Missing dictionary: '+name)
    start = match.end()
    depth = 1
    for index in range(start, len(text)):
        depth += (text[index] == '{') - (text[index] == '}')
        if depth == 0:
            return text[start:index]
    raise ValueError('Unclosed dictionary: '+name)


def value(text, key):
    return float(re.search(r'\b'+key+r'\s+([^;]+);', text)[1])


def build():
    import cantera as ct
    if ct.__version__ != '3.2.0':
        raise ValueError('Use Cantera 3.2.0')
    reference = ct.Solution('gri30.yaml')
    text = (INPUTS/'thermo.inputData_GRI').read_text()
    names = re.search(r'species\s+53\s*\((.*?)\)\s*;', text, re.S)[1].split()
    species, weights = [], {}
    for name in names:
        data = block(text, name)
        coeff = lambda key: list(map(float, re.search(key+r'\s*\((.*?)\)', data, re.S)[1].split()))
        item = reference.species(name)
        item.thermo = ct.NasaPoly2(value(data, 'Tlow'), value(data, 'Thigh'), 101325,
            [value(data, 'Tcommon')]+coeff('highCpCoeffs')+coeff('lowCpCoeffs'))
        species.append(item)
        weights[name] = value(data, 'molWeight')
    base = ct.Solution(thermo='ideal-gas', kinetics='gas', species=species)
    kinetics = (INPUTS/'reactionsGRI').read_text()
    definitions = []
    for index in range(325):
        data = block(kinetics, 'un-named-reaction-'+str(index))
        kind = re.search(r'\btype\s+(\w+);', data)[1]
        equation = re.search(r'\breaction\s+"([^"]+)"', data)[1]
        # OF writes 2CO. Cantera requires a space after stoichiometric numbers.
        equation = re.sub(r'\b(\d+)([A-Z])', r'\1 \2', equation)
        left, right = equation.split(' = ')
        arrow = ' => ' if kind.startswith('irreversible') else ' <=> '
        def rate(body):
            return {'A': value(body, 'A'), 'b': value(body, 'beta'),
                    'Ea': value(body, 'Ta')*ct.gas_constant}
        definition = {}
        if 'FallOff' in kind or 'ThirdBody' in kind:
            efficiencies = block(data, 'thirdBodyEfficiencies') if 'FallOff' in kind else data
            definition['efficiencies'] = {n:float(v) for n,v in
                re.findall(r'\((\S+)\s+([\d.eE+\-]+)\)', efficiencies)}
            if len(definition['efficiencies']) != 53:
                raise ValueError('Incomplete collision efficiencies')
            definition['default-efficiency'] = 1.0
        if 'FallOff' in kind:
            left += ' (+M)'; right += ' (+M)'
            definition.update(type='falloff', **{'low-P-rate-constant':rate(block(data,'k0')),
                'high-P-rate-constant':rate(block(data,'kInf'))})
            if 'Troe' in kind:
                f = block(data, 'F')
                definition['Troe'] = dict(A=value(f,'alpha'), T3=value(f,'Tsss'),
                                          T1=value(f,'Ts'), T2=value(f,'Tss'))
        else:
            if 'ThirdBody' in kind:
                left += ' + M'; right += ' + M'
                definition['type'] = 'three-body'
            definition['rate-constant'] = rate(data)
        definition['equation'] = left+arrow+right
        definitions.append(definition)
    reactions = [ct.Reaction.from_dict(d, base) for d in definitions]
    # Canonical stoichiometry detects duplicate equations despite term order.
    signature = lambda r: (tuple(sorted(r.reactants.items())),tuple(sorted(r.products.items())),r.reaction_type)
    counts = Counter(signature(r) for r in reactions)
    for reaction in reactions:
        reaction.duplicate = counts[signature(reaction)] > 1
    gas = ct.Solution(thermo='ideal-gas', kinetics='gas', species=species,
                      reactions=reactions, transport_model='mixture-averaged')
    provenance = {'cantera_version':ct.__version__, 'species':gas.n_species,
        'reactions':gas.n_reactions, 'inputs':{n:hashlib.sha256((INPUTS/n).read_bytes()).hexdigest()
        for n in ['reactionsGRI','thermo.inputData_GRI']},
        'transport_source':'Cantera 3.2.0 bundled gri30.yaml',
        'maximum_molecular_weight_relative_difference':max(abs(gas.molecular_weights[i]/weights[n]-1)
            for i,n in enumerate(names)),
        'rate_conversion':'A retained in m/kmol/s; Ea=Ta*Cantera R; author rounded NASA7 retained'}
    return gas, weights, provenance
