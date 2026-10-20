// Deliberately includes no Cantera headers and can use a different C++ ABI.
#include "bridge.h"
#include <dlfcn.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
template<class T>T symbol(void* library,const char* name) {
    auto address=dlsym(library,name);
    if(!address)throw std::runtime_error(dlerror());
    return reinterpret_cast<T>(address);
}
std::vector<std::string> split(const std::string& line) {
    std::stringstream stream(line);std::string word;std::vector<std::string> values;
    while(std::getline(stream,word,',')) {
        if(!word.empty() && word.back()=='\r')word.pop_back();values.push_back(word);
    }
    return values;
}
int main(int argc,char** argv) {
try {
    if(argc!=6)throw std::runtime_error("Usage: bridge-probe LIBRARY INPUTS STAGE OPTIONS PROFILE");
    void* library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if(!library)throw std::runtime_error(dlerror());
    auto create=symbol<decltype(&rf_ct_create)>(library,"rf_ct_create");
    auto destroy=symbol<decltype(&rf_ct_destroy)>(library,"rf_ct_destroy");
    auto evaluate=symbol<decltype(&rf_ct_evaluate)>(library,"rf_ct_evaluate");
    auto error=symbol<decltype(&rf_ct_error)>(library,"rf_ct_error");
    auto count=symbol<decltype(&rf_ct_species_count)>(library,"rf_ct_species_count");
    auto name=symbol<decltype(&rf_ct_species_name)>(library,"rf_ct_species_name");
    char message[4096];auto* context=create(argv[2],std::stoi(argv[3]),argv[4],message,sizeof(message));
    if(!context)throw std::runtime_error(message);
    for(const char* option:{"fine-grid","mass-gradient","total-enthalpy",
                            "total-enthalpy,pure-species-flux",
                            "bounded-takahashi,takahashi-table2,takahashi-bulk"}) {
        auto* invalid=create(argv[2],1,option,message,sizeof(message));
        if(invalid) {destroy(invalid);throw std::runtime_error("Flow-only option accepted by property bridge");}
        if(std::string(message).find("not property or reactor")==std::string::npos)
            throw std::runtime_error("Missing actionable flow-option rejection");
    }
    if(count(context)!=53)throw std::runtime_error("Unexpected species count");
    std::ifstream file(argv[5]);std::string line;std::getline(file,line);auto columns=split(line);
    if(columns.size()!=60)throw std::runtime_error("Profile width");
    for(size_t k=0;k<53;k++) {
        if(name(context,k,message,sizeof(message)))throw std::runtime_error(error(context));
        if(columns[k+7]!="Y_"+std::string(message))throw std::runtime_error("Profile species order");
    }
    std::vector<std::vector<double>> rows;
    while(std::getline(file,line)) {
        auto fields=split(line);if(fields.size()!=60)throw std::runtime_error("Profile row width");
        std::vector<double> row;for(auto& field:fields)row.push_back(std::stod(field));rows.push_back(row);
    }
    if(rows.empty())throw std::runtime_error("No profile rows");
    double largest=0,massError=0,eulerError=0;size_t checked=0;
    std::vector<double> h(53),d(53),w(53);rf_ct_properties properties;
    for(size_t j=0;j<rows.size();j+=std::max<size_t>(1,rows.size()/50)) {
        auto& row=rows[j];
        if(evaluate(context,row[1],10132500,row.data()+7,53,&properties,h.data(),d.data(),w.data()))
            throw std::runtime_error(error(context));
        std::vector<double> actual={properties.density,properties.enthalpy,properties.cp,properties.conductivity};
        for(size_t i=0;i<actual.size();i++)largest=std::max(largest,std::abs(actual[i]-row[i+3])/std::max(1.,std::abs(row[i+3])));
        double sum=0,norm=0,hmix=0;
        for(size_t k=0;k<53;k++){sum+=w[k];norm+=std::abs(w[k]);hmix+=row[k+7]*h[k];}
        massError=std::max(massError,std::abs(sum)/std::max(norm,1e-30));
        eulerError=std::max(eulerError,std::abs(hmix-properties.enthalpy)/std::max(1.,std::abs(properties.enthalpy)));
        auto originalDiffusion=d;double originalConductivity=properties.conductivity;
        if(evaluate(context,row[1],10132500,row.data()+7,53,&properties,nullptr,d.data(),nullptr))
            throw std::runtime_error(error(context));
        if(d!=originalDiffusion || properties.conductivity!=originalConductivity)
            throw std::runtime_error("Transport-only query differs from complete evaluation");
        checked++;
    }
    auto y=std::vector<double>(rows[0].begin()+7,rows[0].end());y[0]=-.01;
    if(!evaluate(context,298,10132500,y.data(),53,&properties,h.data(),d.data(),w.data()))
        throw std::runtime_error("Negative composition accepted");
    if(!evaluate(context,298,10132500,rows[0].data()+7,52,&properties,h.data(),d.data(),w.data()))
        throw std::runtime_error("Wrong species count accepted");
    std::cout<<"states="<<checked<<" maximum_scaled_property_error="<<largest
        <<" mass_source_relative_error="<<massError<<" enthalpy_Euler_error="<<eulerError<<'\n';
    if(largest>1e-8 || massError>1e-8 || eulerError>1e-8)throw std::runtime_error("Bridge parity/conservation failed");
    destroy(context);dlclose(library);
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
