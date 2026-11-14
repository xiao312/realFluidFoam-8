#include "relaxedTable.H"
#include "psiReactionThermo.H"
#include "makeCombustionModel.H"
namespace Foam
{
    makeCombustionModel(relaxedTable, psiReactionThermo);
}
