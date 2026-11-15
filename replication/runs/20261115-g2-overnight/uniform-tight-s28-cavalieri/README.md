# S28 explicit ordinary and final species tolerance control

Fresh original-zero Cavalieri 2ms, maxdt0.5us, exact10us source. Both Yi and
YiFinal explicitly use 1e-12; all other physics, fields, clipping and acceptance
remain unchanged. S23/S26 ordinary Yi was1e-12 but final YiFinal selected the
broader1e-8 regex. Their completed data and failures remain retained; they are
partially tightened controls. This is an experimental configuration correction,
not a proven caloric repair or paper agreement. Reuses source6b02d79/solver5a83
and all15 pinned products; no new build or library ABI change.

Inputs: frozen factory/table/mesh, original-zero initialization, S23 runtime.
Outputs: new case/results only, ordinary/final dictionary binding receipt,
physical profiles and unchanged conservation/closure diagnostics.
Dependencies: qualified OF8 runtime and FlamePilot Slurm adapter. No credentials
are included. Node syntax and strict Bash checks precede admission. Executing
foamDictionary must read1e-12 for both entries before decomposition/CFD.
Example: adapter.local.py plan --request REQUEST (operator-generated JSON).
No scheduler success or synthetic check constitutes scientific acceptance.
