"""Independent checks of mechanism translation and seed conservation."""
from collections import defaultdict
import json
from pathlib import Path
import unittest
from mechanism import build


class BaselineTests(unittest.TestCase):
    def test_forward_rates_against_bundled_gri30(self):
        import cantera as ct
        gas,_,_=build()
        reference=ct.Solution('gri30.yaml')
        self.assertEqual((gas.n_species,gas.n_reactions),(53,325))
        composition={n:1+i/53 for i,n in enumerate(gas.species_names)}
        def grouped(model):
            values=defaultdict(float)
            for reaction,rate in zip(model.reactions(),model.forward_rates_of_progress):
                key=(tuple(sorted(reaction.reactants.items())),tuple(sorted(reaction.products.items())))
                values[key]+=rate
            return values
        for temperature in [500,1000,1800,2300]:
            gas.TPX=reference.TPX=temperature,10132500,composition
            a,b=grouped(gas),grouped(reference)
            self.assertEqual(set(a),set(b))
            # Author Ta differs slightly from bundled Ea/R. HCN dissociation
            # differs by 0.7212% at 500 K (both rates below 1e-39 here).
            # Check translation within 1%, not exact database equivalence.
            error=max(abs(a[k]/b[k]-1) for k in a if b[k]>1e-100)
            self.assertLess(error,.01)

    def test_all_seed_conditions_and_normalization(self):
        seeds=json.loads(Path(__file__).with_name('seeds.json').read_text())
        self.assertEqual(len(seeds),11)
        for seed in seeds.values():
            self.assertEqual(seed['pressure_Pa'],10132500)
            self.assertEqual(seed['unburned']['temperature_K'],298)
            self.assertLess(seed['enthalpy_relative_error'],1e-8)
            for state in ['unburned','burned']:
                self.assertEqual(len(seed[state]['mass_fractions']),53)
                self.assertAlmostEqual(sum(seed[state]['mass_fractions'].values()),1,places=12)


if __name__=='__main__':unittest.main()
