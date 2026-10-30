#include "steadyFlamelet.H"
#include "psiReactionThermo.H"
#include "makeCombustionModel.H"
namespace Foam
{
    makeCombustionModel(steadyFlamelet, psiReactionThermo);
}
