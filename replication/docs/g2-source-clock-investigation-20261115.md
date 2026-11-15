# G2 source-clock investigation

The owner authorized further investigation after the closed baseline campaign.
This work does not reopen that campaign or reset its 85-job accounting.

## Measured state comparison

Sixteen selected cells were read from the completed Schmitt/Cavalieri 5 ms
fields. Exact 53-species compositions, Z, p, T, h, Ha, rho, c, Qdot and table
diagnostics were retained with hashes. Archives were read in memory to preserve
the H/h name distinction on Windows. These states are not CFD restart inputs.

At the Schmitt global hot cell, Z=0.206798, T=1983.992 K and the exact executed
table diagnostic is 3486.677 K. CO+CO2 is 52.89% of the table target, and the
species L1 difference is 0.87760. The Cavalieri hot cell has Z=0.239299,
T=2215.114 K versus target 3446.594 K, progress 59.74% and L1 difference 0.77292.
Thus the flow reaches near-stoichiometric mixtures but its composition lags the
retained target. This supports investigating source relaxation. It does not
prove that all temperature error is a source error or validate the target table.

Cold-interface states retain a separate temperature/composition inconsistency
with that target. Existing cryogenic caloric failures and root diagnostics must
remain. Faster relaxation could expose those failures rather than repair them.

## Controlled alternative

Schmitt (2020), Eq.12, uses numerical per-step relaxation with Cr100. It remains
the default and the paper-control path. Its effective time is Cr*deltaT, which
changes under adaptive stepping. No coding defect is inferred from that choice.

An opt-in fixedTime control uses alpha=deltaT/tau in the same convex species
update. Choose tau before examining a new result; do not fit it to temperature.
The first 10 microsecond control corresponds to the earlier fine-step Cr100
baseline's source time. A separate 50 microsecond control can diagnose a source
time range; neither is a newly validated chemical model. Maximum deltaT must
not exceed tau. No coefficient, species limit, EOS parameter or energy source
is adjusted. Formation heat remains diagnostic in the absolute-Ha equation.

The clock header changes no class layout or virtual interface. Rebuild the
combustion implementation and solver against explicitly pinned parent products.
Record every resolved DSO; distinguish fourteen reused libraries from the new
combustion DSO. A build/help check alone does not qualify numerical behavior.

## Execution and verdicts

First require real one-cell default recurrence and matched-alpha fixed-time
parity, with retained invalid-control evidence. Then run independently initialized
adaptive G2 controls: steps100 and fixedTime10 microseconds. Compare at common
physical times, including the previous fine-step baseline where available.
Preserve failures. Do not substitute output from one source clock for another.

Evaluate temperature fields, species-to-target distance, source element changes,
mass/energy budgets and caloric closure. Better temperature alone is insufficient.
No failed acceptance criterion blocks separately justified diagnostic preparation.
No evolved CFD states, arbitrary added heat, chemistry fitting or hidden clipping.

The fixed-time mode is a hypothesis test. A successful case does not establish
LES/PDF, source-transport conservation, developed statistics or a G2 paper pass.
Results and full input/product identities belong in the central Forge comparisons.

## Executed evidence

The retained5ms logs report deltaT5us and Cr100 tau500us in both cases; the prior fine-step0.1us setting implied10us. The nominal relaxation scale changed50-fold. This is an observed numerical timescale change, not a fitted chemistry rate.

Source d020b8d compiled and linked in Slurm128102177,335s,solver SHA25629ed7066d2d0b7ff84a4cffaee766fa46d7de31ab78595bfe3cca1991d720fa3.15library products pinned,14actuallyloaded,onefreshcombustionDSO.40actualsource rows passed; equal-alpha modes had exactly equal numerical results and invalidtau was rejected. Default flow profiles at actual20.4651195144us match retained baseline profiles exactly across32000numericalvalues in two conditions. These checks preserve the default; they do not validate the new clock physically.

Actual-runtime enthalpy queries in128102509,361s,converged for8compositions from3guesses each. At the same capturedHa/p,the target compositions recover3399.54K(Schmitt hottest),3315.00K(Schmitt15mm),3361.73K(Cavalieri hottest),3383.86K(Cavalieri15mm). Captured compositions recover their original1983.99/1507.35/2215.11/1495.98K states. Thus highT is locally compatible with transportedHa in these four hot cells. This does not qualify cryogenic branches,element conservation,chemical equilibrium or globalenergy.

The first physical wrapper128102594 failed beforeCFD due a legacy case-prefix restriction. Corrected S02b packets retain the inlet helper and use fresh compatible names;128102962/128103070 are the independently admitted Schmitt/Cavalieri paired controls. Both initial steps-mode cases advanced; fixedTime data remains pending at this update. All failures,admission refusals and exactreceipts remain operator evidence. No new5ms field is claimed yet.
