#include "ConservativeFlow.h"
#include "cantera/base/Solution.h"
#include <iostream>

using namespace Cantera;

void require(bool condition,const char* message) {
    if(!condition)throw std::runtime_error(message);
}

class Probe : public hydrogen::ConservativeFlow {
public:
    explicit Probe(std::shared_ptr<Solution> solution)
        : hydrogen::ConservativeFlow(solution) {setFreeFlow();}

    double telescoping=0,uniformDifference=0,nonuniformDifference=0;
    double speciesSum=0,locality=0,perturbationLocality=0;

    void verify(bool uniform,double massFlow,double inverseTime,bool varyingMass) {
        const std::vector<double> grid=uniform?
            std::vector<double>{0,1,2,3,4,5,6}:
            std::vector<double>{0,.2,.7,1.1,2,3,5};
        setupGrid(grid.size(),grid.data());
        std::vector<double> state(size(),0),old(size(),0),actual(size(),0),local(size(),0);
        std::vector<int> oldDiagonal(size(),0),diagonal(size(),0),localDiagonal(size(),0);
        for(size_t j=0;j<m_points;j++) {
            m_rho[j]=1.+.25*j;
            state[index(c_offset_U,j)]=massFlow*(1+(varyingMass?.03*j:0.))/m_rho[j];
            state[index(c_offset_T,j)]=298;
            state[index(c_offset_Y,j)]=.1+.03*j;
            state[index(c_offset_Y+1,j)]=.3-.01*j;
            state[index(c_offset_Y+2,j)]=.6-.02*j;
            for(size_t k=0;k<m_nsp;k++) {
                const double source=k==0?.01*j:k==1?-.01*j:0.;
                m_wdot(k,j)=source/m_wt[k];
                if(j+1<m_points)
                    m_flux(k,j)=(k==0?.02:k==1?-.015:k==2?-.005:0.)*(j+1);
            }
        }
        m_slast=state;
        for(size_t j=0;j<m_points;j++) {
            m_slast[index(c_offset_Y,j)]+=.005;
            m_slast[index(c_offset_Y+2,j)]-=.005;
        }
        Flow1D::evalSpecies(state.data(),old.data(),oldDiagonal.data(),
                            inverseTime,0,m_points-1);
        evalSpecies(state.data(),actual.data(),diagonal.data(),inverseTime,0,m_points-1);
        evalSpecies(state.data(),local.data(),localDiagonal.data(),
                    inverseTime,2,m_points-3);
        for(size_t j:{size_t(0),m_points-1})
            for(size_t k=0;k<m_nsp;k++) {
                const auto i=index(c_offset_Y+k,j);
                require(actual[i]==old[i] && diagonal[i]==oldDiagonal[i],
                        "Boundary species row changed");
            }
        for(size_t k=0;k<m_nsp;k++) {
            double residualIntegral=0,sourceIntegral=0;
            for(size_t j=1;j+1<m_points;j++) {
                const auto i=index(c_offset_Y+k,j);
                const double cellWidth=.5*(grid[j+1]-grid[j-1]);
                residualIntegral+=cellWidth*m_rho[j]*
                    (actual[i]+inverseTime*(state[i]-m_slast[i]));
                sourceIntegral+=cellWidth*m_wt[k]*m_wdot(k,j);
                require(diagonal[i]==1,"Interior pseudo-time diagonal changed");
                const double difference=std::abs(actual[i]-old[i]);
                if(uniform && !varyingMass)uniformDifference=std::max(uniformDifference,difference);
                else if(!uniform)
                    nonuniformDifference=std::max(nonuniformDifference,difference);
                if(j>=2 && j<=m_points-3)
                    locality=std::max(locality,std::abs(actual[i]-local[i]));
            }
            // Only the two external faces enter this independent global balance.
            const size_t leftUp=massFlow>=0?0:1;
            const size_t rightUp=massFlow>=0?m_points-2:m_points-1;
            const double rightMass=massFlow*(1+(varyingMass?.03*(m_points-1.5):0.));
            const double leftMass=massFlow*(1+(varyingMass?.015:0.));
            const double boundaryOut=rightMass*state[index(c_offset_Y+k,rightUp)]
                +m_flux(k,m_points-2);
            const double boundaryIn=leftMass*state[index(c_offset_Y+k,leftUp)]
                +m_flux(k,0);
            telescoping=std::max(telescoping,
                std::abs(residualIntegral-sourceIntegral+boundaryOut-boundaryIn));
        }
        for(size_t j=1;j+1<m_points;j++) {
            double sum=0;
            for(size_t k=0;k<m_nsp;k++)sum+=actual[index(c_offset_Y+k,j)];
            const double massDivergence=varyingMass?
                massFlow*.03/(.5*(grid[j+1]-grid[j-1])):0.;
            speciesSum=std::max(speciesSum,std::abs(sum+massDivergence/m_rho[j]));
        }
        for(size_t component:{size_t(c_offset_U),size_t(c_offset_Y)}) {
            auto perturbed=state;
            perturbed[index(component,3)]+=1e-7;
            std::vector<double> full(size(),0),partial(size(),0);
            evalSpecies(perturbed.data(),full.data(),diagonal.data(),
                        inverseTime,0,m_points-1);
            evalSpecies(perturbed.data(),partial.data(),localDiagonal.data(),
                        inverseTime,2,4);
            for(size_t j=1;j+1<m_points;j++)
                for(size_t k=0;k<m_nsp;k++) {
                    const auto i=index(c_offset_Y+k,j);
                    const double expected=j>=2 && j<=4?partial[i]:actual[i];
                    perturbationLocality=std::max(perturbationLocality,
                                                 std::abs(full[i]-expected));
                }
        }
    }
};

int main(int argc,char** argv) {
try {
    require(argc==2,"Usage: test-conservative IDEAL_YAML");
    auto solution=newSolution(argv[1],"","mixture-averaged");
    require(solution->thermo()->nSpecies()>=3,"At least three fixture species required");
    Probe probe(solution);
    for(bool uniform:{false,true})
        for(double flow:{-.7,.7})
            for(double inverseTime:{0.,4.})
                for(bool varyingMass:{false,true})
                    probe.verify(uniform,flow,inverseTime,varyingMass);
    require(probe.telescoping<1e-13,"Global species balance failed");
    require(probe.uniformDifference<1e-13,"Uniform-grid stock equivalence failed");
    require(probe.nonuniformDifference>1e-3,"Fixture does not distinguish old stencil");
    require(probe.speciesSum<1e-13,"Summed species normalization residual failed");
    require(probe.locality==0,"Partial residual range changed interior results");
    require(probe.perturbationLocality==0,"Perturbation exceeds nearest-neighbor stencil");
    std::cout<<"PASS 16 residual fixtures; telescoping "<<probe.telescoping
             <<" uniform "<<probe.uniformDifference
             <<" distinguishing_nonuniform "<<probe.nonuniformDifference
             <<" summed_species "<<probe.speciesSum<<" partial_range "<<probe.locality
             <<" perturbation_locality "<<probe.perturbationLocality<<'\n';
} catch(const std::exception& error) {
    std::cerr<<error.what()<<'\n';return 1;
}
}
