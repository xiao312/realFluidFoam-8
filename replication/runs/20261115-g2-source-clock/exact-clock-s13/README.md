# Exact frozen-target source qualification

Build the optional fixedTimeExact clock against the pinned R54 libraries.
Inputs: frozen source archive/source.json, existing S01/R54 products and full53
probe inputs. Outputs: compile/link hashes, old-runtime rejection, unchanged
steps/Euler parity, invalid-time rejection and actual 20/40-step model probes
at equal physical source time. No flow steps, paper acceptance or scheduler
implementation occurs here. No credentials are inputs. main.sh runs only in a
FlamePilot-admitted OF8 allocation. verify-exact.mjs validates actual CSV alpha,
recurrence, caloric/Qdot/Ha checks and equal-time endpoint temperature.

Example: bash -euo pipefail /workspace/inputs/exact-clock-s13/main.sh.
Expected: explicit EXACT_CLOCK_BUILD_SOURCE_QUALIFIED and retained receipts.
A successful source control is necessary for this experiment, not reacting G2
validation. Default per-step and prior Euler controls remain available.
