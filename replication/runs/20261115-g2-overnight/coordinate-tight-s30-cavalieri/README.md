# S30 transported-coordinate consistency control

Test whether unequal equation solution tolerances contribute to source elemental
drift: ordinary/final Z now1e-12, matching existing Yi/YiFinal1e-12. All EOS,
chemistry, source clock(exact10us), Ha/pressure algorithms, clipping and acceptance
are unchanged. It is a numerical convergence hypothesis, not chemical fitting.
Fresh original-zero Cavalieri300us/maxdt0.5us, same mesh/inlets/table/runtime.
Inputs are frozen S28 controls; output new case/profiles and unchanged diagnostics.
Field writes100us accommodate300us endpoint; profiles remain100us. Four exact
solver entries are checked by executing foamDictionary before decomposition/CFD.
Dependencies: qualified source6b02/solver5a83/all15products and OF8/FlamePilot.
No credentials, restarts or mixed builds. Node syntax and manifest/Bash checks
precede admission; compare actual source maxElementChange and matched300us
profiles against S28. Success means a measured improvement, never just process0.
Example: adapter.local.py plan --request REQUEST. Require known free slot and
2400s wall fitting before09:20Shanghai; do not cancel productive controls.
