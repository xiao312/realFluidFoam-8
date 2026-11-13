# Maders coflow ignition investigation —13November2026

The broad single-ignition kernel is the first physical control that sustains the
new quenching-table flame beyond the initial temperature collapse. It has not yet
established a steady coflow or agreement with Maders Figure4. Fresh full cases
follow; the old sparse-table flame is retained as a failed comparison.

## Evidence and decisions

The earlier paper-aligned sparse-table run127906458 stopped normally after21202s.
Its last retained1.390s sample has temperature RMS380/746K at H10/H40, versus the
previous baseline347/697K. The final100ms changes are500/593K: not steady.
New-table case127908321 extinguished and stopped at1.2368s. Both failures remain
in the comparison gallery. No evolved state is reused.

Exact C++ table replay (source512fa7e, job127938538) and Cantera3.2/DRM19
constant-pressure reactors expose a cold-progress discrepancy. At stoichiometric
Z, initial C=.001, old-table replay grows to.0409826 in20ms; direct chemistry
reaches.001022553. New-table replay.001000183 versus direct.001000031 is much
closer. Fixed-density replay and constant-pressure chemistry use different density
treatments; cold-state density changes are small. Initial instantaneous rates
alone miss radical relaxation. At C=.03 the new trajectory remains discrepant;
this does not qualify all chemistry or justify fitting reaction constants.

The ignition event changed density after timestep selection on cold flow. The
legacy first following Courant number reached2.15577 with maxCo=.5. Sourceea2a404
refreshes mass flux, preserves the MRF-relative operation, caps the ignition step
at1e-6s and reselects the adaptive step. The actual corrected event selected
1.19949e-6s; the following Co was.136821. Absolute-Ha ownership is unchanged.

| Fresh diagnostic | Last physical time,s | Peak T,K | Heat release,W | Outcome |
|---|---:|---:|---:|---|
| Legacy/narrow |.04000|333.34|1.32e-5|Extinguished |
| Narrow,half timestep |.04000|333.80|1.32e-5|Extinguished |
| Narrow,upper-progress seed |.04000|331.13|1.19e-5|Extinguished |
| Narrow,event reset |.04000|331.00|1.01e-5|Extinguished |
| Broad Z=.02–.40,legacy event |.029146|2030.00|1.688|Partial,burning at700s limit |
| Broad Z=.02–.40,event reset |.029882|2030.55|1.628|Partial,burning at700s limit |

Matrices127939138/127939763 both completed their wrappers (2129/1556s); broad
subcases exit124 at their diagnostic guard, so they are not completed40ms runs.
All cases start at0,ignite once around.0101s,120000cells,32ranks. No maintained
heat source is added. Burning for20ms may consume the ignition kernel; full
cold-flow development and sustained anchoring still require measurement.

## Full-length follow-up

Job127943044: fresh cold flow to.9s,then one broad ignition,Z=.02–.40,sourcePeak,
event reset enabled, target2s. Job127943180: fresh moderate-kernel screen,Z=.04–.30,
.01s ignition/.025s end; only if complete with peakT>1600K and Qdot>.05W does it
prepare a separate fresh full case with.9s ignition. This is an operational
survival screen,not science acceptance. All starts are0,never a restart.

Compiled solver sourceea2a4046ab239ae4fdb1197cd65fd83ebc933785; executableSHA256
31b6739c6fa57f9da4d05f8d2e4edf64cd04fe4324176ab9b8dc6ee66d850a78.
Case recipebb3033ec569829fe5035bc925d9225110c9bfbba; physical tableSHA256
35a6b46b5a56d2831a598acb7810119b6bc27ced27d90d217d2258514295c1cc.
FlamePilot adapter0d2a63b546e180facdb6f1c736077517daa5c78c;
OF8 profilef46b172cd5e40693c14e09ae43ca85df418ed3da7556e58fd71fad5b2fca1793.
Both allocations32ranks/64GiB,maximum43200s,within the owner-authorized
14November2026 11:59Shanghai deadline. Prior usage is retained.

The case keeps the paper-aligned mesh/boundaries/inlet and absolute-Ha coupling.
Radial T/CO at10/40mm,axial coordinate/source profiles,patch mass fluxes and
energy diagnostics are recorded. Temporal checks retain the existing.9s+two
flow-through minimum and50/100ms windows; passing is distinct from paper agreement.
Paper lines and our markers remain visible for every result,including failures.

Raw fields/logs remain under the configured SCNet trial. Local state contains the
immutable requests,identities,submission receipts,terminal matrix tails and JSON,
source replay,and original comparison data. No scientific acceptance is asserted.
