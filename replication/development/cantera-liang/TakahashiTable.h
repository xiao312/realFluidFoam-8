#pragma once
#include <cmath>
namespace liang {
// Table 2, Takahashi, JCEJ 7, 417--420, DOI 10.1252/jcej.7.417.
// Cantera 3.2 uses B=3.39031 instead of printed B=2.39031 at Pr=3.
// Add this difference to its correlation; no other row or limit is changed.
inline double takahashiTable2Delta(double pr,double tr) {
    if(pr<=2.5 || pr>=4)return 0;
    double weight=pr<=3?(pr-2.5)/.5:4-pr;
    double common=1.05*.502100*(1-.602907*std::pow(tr,-6.19043));
    return weight*common*(std::pow(tr,-3.39031)-std::pow(tr,-2.39031));
}
}
