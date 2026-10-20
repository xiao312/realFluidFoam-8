#ifndef PROFILE_HEADER
#define PROFILE_HEADER "Profile.h"
#endif
#include PROFILE_HEADER
#include <cstdlib>
#include <iostream>
#include <limits>

void require(bool value,const char* message) {
    if(!value)throw std::runtime_error(message);
}
void writeFixture(const std::filesystem::path& file,const std::string& trace) {
    std::ofstream stream(file);
    stream<<"x_m,T_K,U_m_s,rho_kg_m3,h_J_kg,cp_J_kgK,lambda_W_mK,Y_H,Y_N2\n";
    for(int j=0;j<10;j++)
        stream<<j<<",298,0.7,1,-12,1000,0.03,"<<trace<<",1\n";
}
int main(int argc,char** argv) {
try {
    require(argc==2 || argc==3,
            "Usage: test-profile-reader NEW_FIXTURE_DIRECTORY [CAPTURED_PROFILE]");
    const std::filesystem::path root=argv[1];
    require(!std::filesystem::exists(root),"Fixture directory already exists");
    std::filesystem::create_directories(root);
    const auto file=root/"profile.csv";
    const std::vector<std::string> accepted={
        "0","-0","0.000001","-1e-15","1.126963797451761e-315",
        "-8.1540533071091e-310","4.9406564584124654e-324","2.2250738585072014e-308"};
    for(const auto& value:accepted) {
        writeFixture(file,value);
        const auto profile=hydrogen::readGuess(file,2);
        require(profile.x.size()==10 && profile.y.size()==2,"Profile dimensions changed");
        for(size_t j=0;j<10;j++) {
            require(profile.x[j]==double(j) && profile.T[j]==298 && profile.u[j]==.7,
                    "Ordinary values changed");
            require(profile.y[1][j]==1,"Other species changed");
            require(profile.y[0][j]==std::strtod(value.c_str(),nullptr),"Trace value changed");
        }
    }
    for(const auto& value:{"1e309","1e-400","nan","inf","0.1junk",""}) {
        writeFixture(file,value);bool rejected=false;
        try {hydrogen::readGuess(file,2);} catch(const std::exception& error) {
            const std::string message=error.what();
            rejected=message.find("row 2, column 8")!=std::string::npos;
        }
        require(rejected,"Malformed or out-of-range field accepted");
    }
    std::cout<<"PASS 8 finite fixtures, 6 rejected fixtures; original trace values preserved\n";
    if(argc==3) {
        std::ifstream stream(argv[2]);std::string line;
        require(bool(std::getline(stream,line)),"Captured profile is missing");
        const size_t columns=1+std::count(line.begin(),line.end(),',');
        require(columns>7,"Captured profile lacks species");
        const auto profile=hydrogen::readGuess(argv[2],columns-7);
        size_t rows=0,subnormal=0;
        while(std::getline(stream,line)) {
            std::stringstream row(line);std::string field;size_t column=0;
            while(std::getline(row,field,',')) {
                if(column>=7) {
                    const double original=std::strtod(field.c_str(),nullptr);
                    require(profile.y[column-7][rows]==original,
                            "Captured species value changed");
                    if(original!=0 && std::abs(original)<std::numeric_limits<double>::min())
                        ++subnormal;
                }
                ++column;
            }
            ++rows;
        }
        require(rows==profile.x.size() && subnormal>0,
                "Captured profile did not exercise finite subnormal values");
        std::cout<<"PASS captured profile: "<<rows<<" rows, "<<subnormal
                 <<" subnormal species values; every species value preserved\n";
    }
} catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
