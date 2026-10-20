#include "DiffusionFlow.h"
#include "cantera/base/Solution.h"
#include <iostream>
#include <numeric>
using namespace Cantera;

class Probe : public hydrogen::MidpointCorrectionFlow<Flow1D> {
public:
    explicit Probe(std::shared_ptr<Solution> solution)
        : hydrogen::MidpointCorrectionFlow<Flow1D>(solution,"probe") {
        const double grid[]={0.,1.};
        setupGrid(2,grid);
    }
    std::vector<double> evaluate(const std::vector<double>& left,
                                 const std::vector<double>& right,bool midpoint) {
        std::vector<double> state(2*nComponents(),0.);
        for(size_t j=0;j<2;j++) {
            const auto& composition=j==0?left:right;
            double inverseWeight=0;
            for(size_t k=0;k<m_nsp;k++) {
                state[index(c_offset_Y+k,j)]=composition[k];
                inverseWeight+=composition[k]/m_wt[k];
                m_diff[k+m_nsp*j]=1.+double(k)/m_nsp;
            }
            m_wtm[j]=1./inverseWeight;
        }
        if(midpoint)updateDiffFluxes(state.data(),0,1);
        else Flow1D::updateDiffFluxes(state.data(),0,1);
        std::vector<double> result(m_nsp);
        for(size_t k=0;k<m_nsp;k++)result[k]=m_flux(k,0);
        return result;
    }
};

int main(int argc,char** argv) {
try {
    if(argc!=2)throw std::runtime_error("Usage: test-midpoint IDEAL_YAML");
    auto solution=newSolution(argv[1],"","mixture-averaged");
    Probe probe(solution);
    const size_t n=solution->thermo()->nSpecies();
    double symmetry=0,conservation=0,uniform=0,legacySymmetry=0;
    for(size_t trial=0;trial<32;trial++) {
        std::vector<double> left(n),right(n);
        for(size_t k=0;k<n;k++) {
            left[k]=1.+((k+3)*(trial+7))%17;
            right[k]=1.+((k+5)*(trial+2))%23;
        }
        const double a=std::accumulate(left.begin(),left.end(),0.);
        const double b=std::accumulate(right.begin(),right.end(),0.);
        for(size_t k=0;k<n;k++){left[k]/=a;right[k]/=b;}
        const auto f=probe.evaluate(left,right,true),reverse=probe.evaluate(right,left,true);
        const auto zero=probe.evaluate(left,left,true);
        const auto legacy=probe.evaluate(left,right,false),legacyReverse=probe.evaluate(right,left,false);
        conservation=std::max(conservation,std::abs(std::accumulate(f.begin(),f.end(),0.)));
        for(size_t k=0;k<n;k++) {
            symmetry=std::max(symmetry,std::abs(f[k]+reverse[k]));
            uniform=std::max(uniform,std::abs(zero[k]));
            legacySymmetry=std::max(legacySymmetry,std::abs(legacy[k]+legacyReverse[k]));
        }
    }
    if(symmetry>1e-13 || conservation>1e-13 || uniform>1e-13 || legacySymmetry<1e-5)
        throw std::runtime_error("Midpoint invariants or distinguishing legacy control failed");
    std::cout<<"32 states: reversal="<<symmetry<<" zero-sum="<<conservation
             <<" uniform="<<uniform<<" legacy-reversal="<<legacySymmetry<<'\n';
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
