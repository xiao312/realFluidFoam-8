# Original-zero flame comparison, 20 October 2026

All eleven native ideal-gas cases completed approximately 200 microseconds from
freshly generated initial fields. The energy-corrected phi=1.10 case completed
as well. The existing inline Lark figures and three-page PDF now replace the
historical restart traces. The JSON evidence file records input CSV hashes,
source/job identities, all endpoints and marker coverage.

At phi=1.10, the final primary T/OH-front estimates are 7.140/7.233 cm/s for
native job 124916221 and 7.333/7.433 cm/s for corrected job 124916226. Their
180–200-us means are 7.0838/7.2022 and 7.2596/7.3970 cm/s. Refined ideal
Cantera job 124934682 gives 7.454695 cm/s. The marker difference and continuing
upward drift prevent a steady-speed claim. A single close final OH sample is
not sufficient evidence of replication.

Stock reactingFoam 124896761 and DeepFlame 124901315 remain independently
completed controls. Their final saved samples near 198.94 us give T/OH speeds
6.626/6.609 and 7.237/7.305 cm/s. Transport differs across these solver families.
The first saved DeepFlame sample is 3.115 ns; its simulation starts from zero.
New native/energy traces have an explicit time-zero record and matching
physical-input hash `74eb13eaa06937c65077d734707102fb3722c7de35884ee5b324d8be01a886d6`.

The plotter now derives recorded start times from the data and checks an
optional declared start. It no longer embeds a historical 50.018-us restart
annotation. The first verification correctly rejected a false claim that the
DeepFlame CSV itself starts exactly at zero. Its declared first observation was
then corrected to 3.115 ns without changing any data. Sweep plots also respect
actual history duration instead of silently limiting future 300-us data to 205 us.
All exports were generated and visually inspected; input hash checks passed.

The new energy-corrected sweep and native phi=1.10 control remain separate
original-zero 300-us jobs, recorded in the pressure-sweep report. No completed
case was resumed. At 01:32 CST, monitored jobs had reached about 24 us with 50-ns
adaptive steps and finite residuals. Time, mesh and domain qualification remain.

Current inline section:
https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf#doxcnzfYKF8IZYcOZG1otuiDnJb

Local exported artifact directory (outside Git):
`output/pdf/flame-speed-original-zero-20261020/`.
