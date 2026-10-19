#include "SrkKernel.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
int main(int argc,char** argv) {
try {
    if(argc!=4 || std::filesystem::exists(argv[3]))throw std::runtime_error("Usage: alpha-probe SPECIES PROFILE NEW_OUTPUT");
    std::ifstream table(argv[1]);std::vector<liang::Species> species;std::vector<std::string> names;
    std::string name;liang::Species s;
    while(table>>name>>s.Tc>>s.Pc>>s.Vc>>s.W>>s.omega>>s.eos){species.push_back(s);names.push_back(name);}
    if(species.size()!=53)throw std::runtime_error("Expected 53 species");
    std::ifstream profile(argv[2]);std::string line,item;std::getline(profile,line);
    std::vector<std::vector<double>> rows;
    while(std::getline(profile,line)) {
        std::stringstream stream(line);std::vector<double> row;
        while(std::getline(stream,item,','))row.push_back(std::stod(item));
        if(row.size()!=60)throw std::runtime_error("Profile schema");rows.push_back(row);
    }
    if(rows.empty())throw std::runtime_error("Empty profile");
    std::ofstream out(argv[3]);out<<std::setprecision(16)
        <<"species,T_cross_K,profile_T_K,X_species,epsilon_K,h_jump_J_kg,smooth_cp_increment_J_kg\n";
    for(size_t k=0;k<species.size();k++) {
        const auto& z=species[k];double m=.48+1.574*z.omega-.176*z.omega*z.omega;
        if(!z.eos || m<=0)continue;
        double T=z.Tc*std::pow(1+1/m,2);
        if(T<298 || T>2400)continue;
        auto row=*std::min_element(rows.begin(),rows.end(),[&](const auto& a,const auto& b){return std::abs(a[1]-T)<std::abs(b[1]-T);});
        std::vector<double> x(53);double sum=0,W=0;
        for(size_t i=0;i<53;i++){x[i]=std::max(0.,row[i+7])/species[i].W;sum+=x[i];}
        for(size_t i=0;i<53;i++){x[i]/=sum;W+=x[i]*species[i].W;}
        for(double epsilon:{.01,.0001,.000001}) {
            auto lo=liang::evaluate(T-epsilon,10132500,x,species);
            auto hi=liang::evaluate(T+epsilon,10132500,x,species);
            out<<names[k]<<','<<T<<','<<row[1]<<','<<x[k]<<','<<epsilon<<','
               <<(hi.h-lo.h)/W<<','<<epsilon*(hi.cp+lo.cp)/W<<'\n';
        }
    }
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
