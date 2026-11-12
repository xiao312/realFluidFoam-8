# Maders Smooke transport adapter

Optional OpenFOAM8 ideal-gas transport registration for the atmospheric coflow.
It implements the paper's Cp-dependent Smooke conductivity and viscosity exactly.
It does not change real-fluid SRK/PR/Chung registrations or grant CFD acceptance.
Inputs: ordinary NASA7/perfectGas multiComponentMixture with transport smooke.
Outputs: mu, kappa and alphah; optional libmadersThermo.so selection. The inherited
const-transport mu/Pr dictionary entries are required placeholders and are ignored
by these three functions. No tunable fitting parameters or network/secret access.

Dependencies: stockOF8 specie/basic/reactionThermo templates and wmake. Dependent:
Maders coflow cases only. Register with the normal stock makeReactionThermos macro.
C++ structure extends the Foundation constTransport template; GPL notices retained.
Example within admitted OF8 compute: `wmake libso` in this directory, then load
libmadersThermo.so in controlDict and select thermoType transport smooke.
Verification: compile and evaluate an actual mixture at several temperatures;
compare mu/Cp=1.67e-8*(T/298)^.51 andkappa/Cp=2.58e-5*(T/298)^.69. Mixture arithmetic
and actual clean-start coflow execution remain required. Help/build alone is not
physical validation. UnityLewisFourier supplies Le=1 separately in the case.
