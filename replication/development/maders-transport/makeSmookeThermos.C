// GPL-3.0-or-later. Registration follows Foundation OF8 psiReactionThermos.C.
#include "multiComponentMixture.H"
#include "psiThermo.H"
#include "psiReactionThermo.H"
#include "hePsiThermo.H"
#include "forGases.H"
#include "makeReactionThermo.H"
#include "smookeTransport.H"

namespace Foam
{
typedef smookeTransport<species::thermo<janafThermo<perfectGas<specie>>, sensibleEnthalpy>> smookeGasHThermoPhysics;
makeReactionThermos(psiThermo, psiReactionThermo, hePsiThermo, multiComponentMixture, smookeGasHThermoPhysics);
}
