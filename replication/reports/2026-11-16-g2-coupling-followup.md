# G2 coupling follow-up, 16 November 2026, 20:45 Shanghai

Owner deadline: 21:00. Every CFD control starts at zero; no acceptance limit was changed. Results remain development evidence, without independent science approval.

## Physical isolation

- Laminar inlet-resolved Kong23 FGM reached 2.115 ms before its existing timeout; the complete 2.1 ms temperature field and raw paper-line/CFD-marker comparisons are retained. The short near-injector flame is not a developed paper mean.
- Cold ramped contrasting O2/CH4 k-epsilon failed around 12.7 microseconds. Frozen turbulence coefficients completed 10 microseconds; this is a diagnostic, not a validated turbulence replacement.
- Uniform methane RANS (128196450) completed 200 microseconds/341 steps with the same flow geometry and prescribed volume velocities. Boundary mass residual is 1.468e-18 kg; Ha state-equation residual is -7.8603e-5 J against 2.8601 J absolute assembled terms. This is an assembled equation budget, not independent total-energy proof. Contrasting fluid properties/coupling remain implicated; a unique root cause is not established.
- Cold full-property Smagorinsky progressed to 122.777 microseconds before the 1200 s child timeout; its accepted 100 microsecond budget is retained. Hot source-peak initialization failed at 1.75598 microseconds with caloric relative defect 0.46524. This is substantial, not a roundoff allowance problem.
- The rejected hot temperature field maps all 10720 cells once and is explicitly labelled rejected. Missing other failed-state fields were not fabricated. The failed multi-field archive attempt remains preserved.

## Code and diagnostics

Boundary calculated diagnostic fields were stale. Candidate bd5d442 rebuilds libcombustionModels and the solver; fourteen other DSOs are identity-checked reuse. Compilation/linking/help succeeded. The old physical control completed but failed its existing assembled-equation residual threshold (6.12486e-4 versus 1e-6). A separate fresh-zero patched control is allowed for diagnostic parity; neither that parity nor a compile receipt erases the original failed physical criterion. No main merge or scientific publication is qualified.

The max-table-temperature hot seed is a separate initialization hypothesis. It is not called equilibrium and does not change chemistry or impose ongoing heat.

## Reuse lead: separate turbulent mass and heat diffusion

OF8 already offers nonUnityLewisEddyDiffusivity for RAS and LES with independent Prt and Sct; its default laminar Lewis number remains one. The header defines mass diffusivity through alphaEff((Prt/Sct)*alphat). The implementation adds species-enthalpy-gradient terms to energy transport. Sources: [official header](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-8/master/src/ThermophysicalTransportModels/turbulence/nonUnityLewisEddyDiffusivity/nonUnityLewisEddyDiffusivity.H), [official implementation](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-8/master/src/ThermophysicalTransportModels/turbulence/nonUnityLewisEddyDiffusivity/nonUnityLewisEddyDiffusivity.C).

Our current SGS diagnostic uses unity turbulent Lewis number at Prt=Sct=0.85; Sharma reports Prt=0.85 and Sct=0.7. Reuse this stock interface rather than creating a second turbulent diffusion framework. Before changing it, verify the energy mapping: our solver passes absolute Ha to divq whereas composition.HE follows the configured thermo energy mapping. If that mapping supplies sensible enthalpy, formation enthalpy must also be included in the cross-diffusion correction. This is an implementation requirement to investigate, not a qualified patch or evidence that the Sct mismatch caused today's instability. Required controls are equal-Prt/Sct identity, homogeneous state, nonuniform species with fixed temperature, and measured boundary energy transport; preserve the existing criteria.

The larger closure gap remains that the current genuine FGM is a single-quench Z/C table; Sharma describes multiple enthalpy levels and a presumed PDF. Captured-state rate replay shows large net-source changes when actual CFD temperature departs from table temperature, especially near reversible-rate cancellation. Do not fit rate factors to paper curves. Develop and test thermally consistent source/enthalpy closure separately from turbulence and ignition.

## Final measured outcomes

The maximum-table-temperature hot SGS seed (128199441) also failed, at3.957553microseconds. The pressure correction became negative near the oxygen-side lip; the worst cell atx=-49.51micrometres/r=2.3368mm reached the pressure and temperature floors1000Pa/60K. Its oxygen mass fraction was0.997826, stored density1125.04kg/m3, and caloric defect190451.9J/kg. Changing the seed did not cure the coupling failure.

Boundary control128200310 completed its physical evolution. Thirty-five internal fields were exactly identical to the original-zero old control; both diagnostic boundary temperatures changed from stale zero to the correct2182.293756K. Both versions retain the same failed assembled-equation residual6.12486e-4 versus1e-6. This qualifies only the narrow diagnostic parity, without scientific acceptance or whole-solver qualification.

Earlier-ignition Maders128196189 ended under its original timeout124 at229.6265ms accepted history. Final complete224.9576ms profiles have temperature RMSE1050/989K and CO RMSE0.02198/0.02720. The lower plane became nearly cold; the upper hot region decayed. All saved history and the final poor comparison were added beside favorable earlier snapshots. Sustained anchoring has not been demonstrated.

Today's two controllers have49 admitted jobs with terminal accounting and no unreceipted operation. Allocated691.4428core-hours include all preparation, builds, failed controls and the long fine/coarse Maders jobs. Nineteen scheduler COMPLETED envelopes are not nineteen science passes; child exits remain authoritative. All cases started atzero, criteria remained unchanged, and no new scientific publication is qualified.
