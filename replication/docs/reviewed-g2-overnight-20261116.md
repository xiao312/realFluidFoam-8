# Reviewed G2 mesh and overnight controls —16November2026

The owner approved the retained200622-cell legacy wedge geometry and allowed cell-size/distribution changes. New17840-cell blockMesh asset preserves the measured3.2mm oxygen bore, straight duct and taper,5.6/10mm methane annulus,13mm casing and upstream outer fluid pocket. The raw injector exit isx10mm, notzero. The legacy chamber ends atx200mm,190mm downstream of that exit. It is an axisymmetric approximation and differs from the paper upstream bore and square chamber.

Job128206561 completed343s: blockMesh/checkMesh passed, both boundary-to-reference edge checks below8.735nm (retained CAD jitter). MeshSHA230be4c288382b2355412ec536fc97e8267b1a63c0548d170c2f1793f4fade52. This qualifies geometry serialization, not reacting physics. The source geometry assets remain unchanged.

C03/128207021 used the existing qualifiedlaminar30a102b runtime, physicalKong table7bd5d213, explicit source-peak seed and analytic duct velocity fromoriginalzero. It failedat20.559us: caloricrelative4.54e-6 versus1e-8, worstabshdifference11.31kJ/kg. A near-exit oxygen-rich cell hadp4.886MPa,T159.609K,Cp15.6MJ/(kgK). Startup pressure excursions and high-Cp caloric branch behavior need separation; no proven correction or paper match is claimed. A separate stationary/ramped cold test and freshzero reacting-ramp sensitivity are recorded under the owner’s09:00November17deadline.

MadersA06/128206646 retains the sameDRM19physicaltable35a6b46b, runtimeea2a4046, inlet/transport and96kgrid asA05, while changing the numericalignitionstate to upperprogress. At15msburningage the upperplane remainscold; T_RMSE752/1138K. This is an early ignition sensitivity, not the paper ignition protocol or a steady flame. The poor result is shown alongside retained earlier comparisons.

Initial coldC02/128206952 failed beforeCFD because the old ramp helper rejected the newly audited geometrymode. Source13eabb8 admits that explicitmode without changing originalzero/stationary/executingdensity contracts. Read-only positive and decomposed-case negative checks passed; C04/128207244 is a distinct freshcase. Preserve the failed attempt.

Cleanup removed only0.05–0.85s intermediate volume outputs from two ended pre-ignition Maderscases:1088directories/38080files/1,992,309,248allocatedbytes movedthroughproject.trash then deleted. ExactplanSHA7b92f49dfe697668a1c6240e656ca2b4a1cb80a1ef67f17dda03f5a685df4480. All inputmeshes, initialstates, buildproducts, tables, logs, plottedprofiles and ignition/laterstates remain retained.

No scientific acceptance or publication is implied. Source commits, compiled runtime, mesh, table, environment and case-control identities remain separate. All compute uses pinnedFlamePilot Slurm0d2a63b andOF8environmentf46b172c; allCFD startsfromzero.
