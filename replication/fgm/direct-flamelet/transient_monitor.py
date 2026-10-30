"""Observe upstream accepted-step positivity clipping without changing its values."""
import importlib
import numpy as np


class ClippingMonitor:
    def __init__(self, gas):
        self.species_count = gas.n_species
        self.element_weights = np.array([[gas.n_atoms(k, element) * gas.atomic_weight(element) / gas.molecular_weights[k]
                                         for element in gas.element_names] for k in range(gas.n_species)])
        self.rows = []

    def __enter__(self):
        self.module = importlib.import_module("spitfire.chemistry.flamelet")
        self.original = self.module.odesolve

        def observed_odesolve(*args, **kwargs):
            upstream_callback = kwargs["post_step_callback"]

            def observed_step(t, state, *callback_args):
                fields = state.reshape((-1, self.species_count))
                explicit_species = fields[:, 1:]
                correction = np.maximum(-explicit_species, 0)
                complete_correction = np.column_stack([correction, -np.sum(correction, axis=1)])
                self.rows.append([float(t), int(np.sum(explicit_species < 0)),
                                  float(np.min(explicit_species)), float(np.min(fields[:, 0])),
                                  float(np.max(correction)),
                                  float(np.max(np.abs(complete_correction @ self.element_weights)))])
                return upstream_callback(t, state, *callback_args)

            kwargs["post_step_callback"] = observed_step
            return self.original(*args, **kwargs)

        self.module.odesolve = observed_odesolve
        return self

    def __exit__(self, *exception):
        self.module.odesolve = self.original

    def summary(self):
        return {"observed_steps": len(self.rows), "changed_upstream_clipping_policy": False,
                "negative_explicit_species_entries": sum(row[1] for row in self.rows),
                "minimum_species_before_clip": min([row[2] for row in self.rows] or [0]),
                "maximum_species_correction": max([row[4] for row in self.rows] or [0]),
                "maximum_element_correction_per_step": max([row[5] for row in self.rows] or [0]),
                "sum_of_max_element_corrections": sum(row[5] for row in self.rows)}
