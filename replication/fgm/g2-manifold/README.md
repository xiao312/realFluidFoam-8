# G2 diffusion FGM preparation

This module stages a genuine raw-progress G2 table experiment by reusing the
pinned Cantera/Spitfire drivers in `../direct-flamelet`. It does not implement
new reaction kinetics, fit paper curves, submit jobs, initialize CFD or approve
a manifold. The existing one-dimensional relaxedY(Z) closure is separate.

`case.json` fixes the TF streams at5.61MPa,85K oxygen and288K methane.
The mechanism path is explicit: the original GRI53 diagnostic and the
author-deposited Zhukov–Kong23/51 mechanism cited by Sharma are separate runs.
No species/rate parameters are fitted. `--integration-config FILE` selects a
hashed numerical variant; omitted means the unchanged `quench.json` default.
`quench-kong-refined.json` tightens temporal/nonlinear error controls and caps
the timestep at2μs after job128170280 exported a physical trajectory but failed
the unchanged2e-10 negative-species table limit (minimum−4.9323e-10). This is a
fresh integration refinement, not permission to discard or repair that failure.
`quench.json` defines a freshHP-equilibrium initial field and an actual unsteady
unity-Le diffusion flamelet at chi_st=1e6/s. This high-chi trajectory samples
extinction states; it is not the scalar dissipation imposed on the CFD flow.
The table transports rawC=YCO2+YCO, with local normalization only for lookup.
Signed volumetric source units remainkg/m3/s. Fixed-pressure ideal-gas chemistry,
Peters chi distribution and cold-Cp extension remain explicit approximations
when coupled to SRK. A table containing finite rows is not a validated FGM.

Inputs: exact mechanism file/hash, source commit, environment receipt hash,
qualified Spitfire runtime with its energy/cold patch receipts, Python path,
and a new output directory. `run.mjs ... --plan` reports all steps without writes.
Application requires a Slurm allocation. Outputs retain the raw trajectory,
clipping/element/enthalpy/rate diagnostics, physical frames, unmodified original
manifest and a separately declared post-peak extinction selection. Existing
`table.py` performs export and held-out checks with unchanged limits and refuses
ambiguous/invalid states. All nonzero exits and logs are preserved. Missing
cold-C=0 coverage remains a reported limitation; no threshold is enlarged here.

Dependencies: Node built-ins, pinned Cantera3.2/Spitfire/NumPy/SciPy, and the
existing direct-flamelet module. No network, secrets, scheduler or agent-runtime
dependency. Consumers are the OF8 table reader and explicit G2 case generator.

```sh
node run.mjs --mechanism /workspace/python-cantera-3.2.0/cantera/data/gri30.yaml \
  --runtime /workspace/build/spitfire-cold-r1 --python /opt/python/bin/python3 \
  --source-commit COMMIT --environment-sha256 SHA256 --out NEW_OUTPUT --plan
```

Verify source/config hashes and runtime patch identity, actual integration time,
finite species and signed sources, held-out error and source/enthalpy/element
consistency. Then test the generated table with the executing OF8 reader and
fresh-zero small transport/ignition cases on the inlet-resolved wedge. Synthetic
lookup checks, compilation and process success are not physical validation.
