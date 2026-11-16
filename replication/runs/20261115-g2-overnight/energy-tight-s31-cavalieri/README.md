# S31 energy linear-accuracy control

Fresh-zero300us Cavalieri, maxdt0.5us/exact10us source. Relative to S30,
ordinary/final h and Ha solvers now1e-12; Yi/YiFinal/Z/ZFinal stay1e-12.
This tests whether the accepted-state versus assembled-energy discrepancy is
explained by energy linear-solve accuracy. No EOS, chemical, Ha ownership,
pressure algorithm, boundary, mesh, clipping or acceptance change. It is a
bounded numerical diagnostic, not an energy-conservation repair claim.
Inputs: frozen S30 controls and qualified6b02/5a83/all15products. Outputs: new
original-zero case,8executing solver-entry checks, profiles and energy/source
diagnostics. Node/OF8 and FlamePilot adapter are required; no credentials.
Example: adapter.local.py plan --request REQUEST. Hashes, Node/strict Bash and
absent owned paths precede admission. Actual matched0–300us accepted energy
versus assembled equation is compared with S30; matrix residual alone is not
global conservation. All scientific acceptance remains false.
2100s allocation/payload1800s must fit before09:20Shanghai. Do not reuse evolved
fields, alter productive cases or relax any existing thermodynamic test.
