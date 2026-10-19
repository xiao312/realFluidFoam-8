# SRK enthalpy discontinuity: 20 October 2026

The original Soave/geometric mixing implementation has finite enthalpy jumps
inside the 100-atm methane/air flame. This is a model limitation, not evidence
that removing a derivative sign would correctly reproduce Liang.

Source before this diagnostic: a10cd1b647a53016b9aa5a918a1a3af1dfddc2e1.
The standalone `alpha_probe.cpp` reads the Case 3 profile from job 124919531,
freezes the nearest composition and evaluates both sides of each species'
crossing temperature, Tc*(1+1/m)^2. At an offset of 1e-6 K:

| Species | Crossing temperature (K) | Departure enthalpy jump (J/kg) |
| --- | ---: | ---: |
| N2 | 1023.557979 | 2339.918156 |
| O2 | 1323.334982 | 398.991606 |
| CO2 | 1448.036550 | 246.309425 |
| CH4 | 1727.874271 | 129.743025 |

The jumps persist as offsets shrink from 0.01 to 1e-6 K; ordinary Cp increments
shrink with the offset. Species sharing a crossing must not be counted twice.
Molecular weights in this diagnostic come from the author species table.
Raw CSV and input profile are retained in operator state, `cantera-liang-20261019`.

Independent energy reconstruction, job 124934721, found a total flux range
relative to peak conduction of 0.2183% on the coarse SRK grid and 0.2157% on
the finer grid. The ideal controls gave 0.0325% and 0.0356%. This suggests a
closure contribution but does not prove the entire residual comes from jumps:
the reconstruction is not Cantera's exact discrete energy residual.

The issue is documented by [Weng and Mevel](https://doi.org/10.1016/j.ijhydene.2023.05.080).
Their analysis distinguishes the derivative sign from the underlying mixing
rule discontinuity. [Giovangigli et al., section 5.2](https://doi.org/10.3934/math.20241270)
give a smooth extension: for x=m*(1-sqrt(T/Tc)), use sqrt(a)/sqrt(ac)=1+A(x),
where A=x for x>=0 and A=x/(1+x^4)^(1/4) for x<0. It preserves the original
subcritical expression and has a positive, decreasing high-temperature tail.

Next test: keep the existing pressure-chemistry sweeps unchanged, implement this
published extension as a separately labelled sensitivity, check enthalpy/Cp
derivatives at the crossings, then compare a Case 3 flame and its energy flux.
Neither this extension nor a signed square root is established as Liang's code.
