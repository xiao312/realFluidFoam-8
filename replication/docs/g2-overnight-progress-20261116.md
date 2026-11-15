# G2 coupling development,16November2026

The fine-step exact-source controls now deliver original-zero1ms cases for both
registered G2 geometries. This is numerical/startup progress; developed paper
means, source element conservation and physical global energy remain unqualified.

## Reproducible changes and controls

- Exact frozen-target source integration: solver source80fa810d34c179d136ce1e45242bc2238d95fddb,
  binary3e62c8e874d32ca161a37ab2ca8f2f21ddc3e3a14d6a51af0fa9183c1ed55de7.
  The default paper-style Cr100 path remains unchanged. Fixed10us is an explicit
  physical-time diagnostic, not a fitted chemical rate or exact paper closure.
- Read-only species predictor audit: source6b02d79fc636c95de6d6fdfe20cea4e72ed72734,
  binary5a83ebca1c787da5076d769f69e50a7b38c21849a1dc364fef8c5f9f54c72736.
  All15custom library products remain pinned to the S13/R54 parent. No library
  ABI change or rebuild. Actual default-off CFD regression matches16000values
  numerically exactly at matched20.0952741922us.
- Controlled input packets are in
  [the overnight run module](../runs/20261115-g2-overnight/README.md). Every case
  begins at its original zero, verifies frozen inputs and executing products,
  and uses the FlamePilot Slurm adapter. No accepted field is reused as zero.

| Control | Exact JobID | Result | Interpretation |
|---|---|---|---|
| S21 Cavalieri,0.5us ceiling,Yi1e-8 |128119943|FAILED4321s at837us; sum error4.16e-6|Species predictor/closure issue, not initiating MPI fault|
| S22b Schmitt,0.5us ceiling,Yi1e-8 |128120313|COMPLETED9536s,1ms|Startup delivery, not developed statistics|
| S23 build/default regression/tight Cavalieri |128125817|COMPLETED5790s, default100us plus independent1ms|Tighter Yi1e-12 passes the species-sum failure with unchanged checks|
| S24 Cavalieri,1us ceiling,Yi1e-12 |128134006|FAILED889s at240.515672us|Separate storedh/EOS caloric inconsistency|
| S25 Schmitt,1us ceiling,Yi1e-12 |128134111|FAILED1442s at233.406266us|Same cold near-injector caloric/coupling pattern|

The case already used oxygen as the closure species. An initial nitrogen-closure
hypothesis was checked and withdrawn without changing the case. S23 retains the
existing clipping and closure formula. Across8040audit records, largest clipping
addition is7.44e-37, source sum error7.55e-15 and relative continuity defect
4.52e-16. This isolates an algebraic-accuracy remedy for the observed S21 failure;
it does not establish all species/element transport as correct.

## Actual physical comparisons

Cavalieri's S23 radial15mm peak is937.35K at1ms, versus the paper's approximately
1800K. The45/70mm planes remain around288K. S12 fine Euler1ms reached813K, but
both source integration and Yi tolerance differ, so the difference cannot be
assigned to either alone. Schmitt's completed1ms case remains a separately
registered geometry/condition. The actual profiles are added as diagnostic views
in the fixed ladder, with paper lines and computed markers; older5ms primaries
remain until a supported longer/common-time candidate improves their comparison.
All75targets,12papers and original captions remain intact.

S23's final caloric relative error2.4184e-9 passes the unchanged1e-8 criterion.
Its measured Euler global mass residual is-1.4148e-15 relative over the retained
boundary-flux interval. The accepted-state equation energy mismatch is0.005853J
againstDeltaH3.968528J; this assembled-equation audit is not an independently
qualified physical boundary-energy budget. EOS/transport density differs by
7.5269e-6. Do not infer full conservation from small matrix residuals.

## Remaining invariant and cold-state problems

The complete53species state at1ms gives max|Zc-Z|3.9044e-4, |Zh-Z|3.0510e-4,
|Zbilger-Z|3.4186e-4 and|Zc-Zh|1.0792e-4. These use the executing molecular
weights and original methane/oxygen stream identities. The table metadata has
exactly the same molecular weights; the129-node table's element mixing-line
error is only4.015e-13. Molecular-weight disagreement and table interpolation
alone therefore do not explain the observed coordinate/composition discrepancy.
The largest per-update source element change is4.4556e-5. Unit species sum does
not qualify elemental conservation. Next trace the weighted species predictor,
boundary transport and source lifecycle; do not hide the defect by fitting or
unreported field projection. These state audits are not integrated element flux
budgets.

S24 retains a full failed-state witness at240.515672101124us: rank0/cell100,
T162.708872K,p5.292647MPa,rho384.010259kg/m3,Ha-447804.987628J/kg. Storedh differs
from executingh(p,T,Y) by4035.076J/kg. This repeats the cold near-injector coupling
pattern seen at coarser steps. The0.5us control reached1ms; a1us ceiling was not
qualified by that success. Limits remain unchanged. Failed snapshots are never
authorized CFD restart inputs.

The separate pure-O2 S20 audit reconstructs3116executing property rows and shows
that two earlier contact rho/e failures enter unstable homogeneous SRK states.
That is not proof that every multicomponent G2 failure requires phase flash.
Low-temperature NASA extrapolation remains unqualified.

## Bounded next runs

S25 failed at162.938389K/5.304348MPa with706.580415J/kg caloric discrepancy;
its actual53species/rho/Ha snapshot is retained and is not a restart input.
S26 Cavalieri128135745 is a separate original-zero3ms control at0.5us. S27
Schmitt128136638 requests a separate original-zero2ms control at0.5us after
the S25 failure. Both retain exact10us source/Yi1e-12 and unchanged physical
acceptance. Their actual outcomes are pending this checkpoint; an admitted
allocation is not completed CFD. The owner compute cutoff is09:20Asia/Shanghai,
16November2026. No production merge or scientific acceptance is claimed.

Detailed immutable receipts, small exports and current operator reports are in
the outer workspace's `state/g2-source-coupling-20261115/overnight-20261115/`.
Raw fields and large histories remain onSCNet. The source Git branch is
`draft/parallel-g2-baseline-20261114`; production `develop/reacting` is untouched.

## 05:00 dated correction and actual longer-run outcome

S26 Cavalieri128135745 failed at1.376ms after7154s:12105.665J/kg caloric discrepancy at160.872K/5.206MPa, rank0/cell250. The last1.3ms four profiles are now visible inForge;15mm peak893K and45/70mm near288K remain poor startup agreement. Original failures and primary best views are retained.

The shorthand Yi1e-12 in prior entries refers only to the ordinary solver. No YiFinal was defined, so final iterations selected the broader1e-8 regex. This is a configuration attribution correction; original1ms completions, raw values and receipts remain unchanged. New original-zero S28/job128145771 explicitly sets both entries to1e-12 and checks them with executing foamDictionary before CFD. Requested2ms/0.5us/exact10us, unchanged physics and acceptance; it is not a demonstrated caloric fix. S27 remains productive at0.721ms on its original partial-tight settings. Recipea486095 is pushed; actual S28 startup pending. Deadline09:20 unchanged; no scientific acceptance or production merge.

05:16 payload verification: S28 began at05:11:55 and reached43.638us after both executing Yi/YiFinal1e-12 binding checks passed. Independent all53-species scalar reconstruction matches85actual library rows and S24/S25/S26 caloric errors. Fixed-rho/Ha S25 recovery is stable (+277148Pa), S24 metastable, S26 unstable intermediate root (isothermal slope-47.44Pa m3/kg); no general pressure correction is qualified. audit-failed-mixtures.py reproduces these diagnostics without scheduler/CFD writes.

Further fixed-pressure largest-root bisection collapses in temperature while retaining enthalpy gaps approximately5.66/2.07/14.52kJ/kg for S24/S25/S26; actual targets lie inside. Finite offsets1e-4 through1e-6K preserve nonzero residuals. This supports selected-root feasibility as a recurring cause; tighter temperature stopping alone cannot bridge the discontinuity. Near-multiple-root conditioning and low-temperature NASA extrapolation remain explicit limitations. No general flash requirement or CFD correction is claimed.

## 07:00 actual profiles and bounded continuation

S27/job128136638 andS28/job128145771 remainRUNNING, latest1.499/1.405ms. S28 now exceeds priorS26failure1.376ms, but terminal2ms and coupling qualification remain pending. At matched1.3ms, tighteningYiFinal lowers15mmpeak893.36to645.91K (paper~1800K);45/70mm remain~288K. This has not improved startup paper agreement. FourCav/Sharma1.3msviews andSchmitt1.4msview added with10byte-exactHTTPchecks; bestprimaries retained. Recent clippingzero/continuity~4e-16 coexist withsourceelementchanges~2-3e-5, stillunqualified.

CompiledS29 sixexact53Y largest/homogeneousGibbs propertyscans are frozen/staged under e548be2, NOTadmitted. Probe599c29fe/parent51075d5 remainpinned; noCFDsteps. GeneralCFDstaginghelper unnecessarily checkedunusedrun.sh; failurepreserved, separatemain-onlyreadonlyhash/strictBash/destinationqualificationpassed. Do notduplicate orstopproductiveCFDtofreeaslot. Admitonlyknownfreeslot and1500sfits09:20cutoff. S26plotmetadata requestedendcorrected1to3msbydatedamendment; originaldata/receiptsretained. Seeoperatorcheckpoint-0700.md/matched-profiles-0700.json/health-0700.json.
