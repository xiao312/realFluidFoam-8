#pragma once
#include "cantera/thermo/ThermoPhase.h"
#include <fstream>
#include <sstream>
#include <unordered_map>

namespace kinetics_control {
inline std::vector<std::string> split(const std::string& line) {
    std::stringstream stream(line);std::string field;std::vector<std::string> result;
    while(std::getline(stream,field,',')) {
        if(!field.empty() && field.back()=='\r')field.pop_back();
        result.push_back(field);
    }
    return result;
}

// This maps a steady numerical guess, not the physical boundary composition.
inline double readGuess(const std::string& file,const Cantera::ThermoPhase& gas,
                        std::vector<double>& grid,std::vector<double>& location,
                        std::vector<double>& temperature,std::vector<double>& velocity,
                        std::vector<std::vector<double>>& massFractions) {
    std::ifstream stream(file);std::string line;
    if(!std::getline(stream,line))throw std::runtime_error("Missing or empty guess");
    const auto header=split(line);
    std::unordered_map<std::string,size_t> columns;
    for(size_t k=0;k<header.size();k++)
        if(!columns.emplace(header[k],k).second)throw std::runtime_error("Duplicate guess column");
    for(const auto* key:{"x_m","T_K","U_m_s"})
        if(!columns.count(key))throw std::runtime_error("Missing guess coordinate/state");
    grid.clear();temperature.clear();velocity.clear();
    massFractions.assign(gas.nSpecies(),{});double discarded=0;
    while(std::getline(stream,line)) {
        const auto fields=split(line);
        if(fields.size()!=header.size())throw std::runtime_error("Guess row width mismatch");
        std::vector<double> values;
        for(const auto& field:fields) {
            const double value=std::stod(field);
            if(!std::isfinite(value))throw std::runtime_error("Nonfinite guess");
            values.push_back(value);
        }
        const double x=values[columns.at("x_m")],t=values[columns.at("T_K")];
        if((!grid.empty() && x<=grid.back()) || t<250 || t>3500)
            throw std::runtime_error("Invalid guess grid or temperature");
        grid.push_back(x);temperature.push_back(t);velocity.push_back(values[columns.at("U_m_s")]);
        double total=0,mapped=0;
        for(size_t k=0;k<header.size();k++)
            if(header[k].rfind("Y_",0)==0)total+=std::max(0.,values[k]);
        for(size_t k=0;k<gas.nSpecies();k++) {
            const auto column=columns.find("Y_"+gas.speciesName(k));
            const double y=column==columns.end()?0.:std::max(0.,values[column->second]);
            massFractions[k].push_back(y);mapped+=y;
        }
        if(mapped<.9 || total<.99 || total>1.01)
            throw std::runtime_error("Guess species mapping loses excessive mass");
        discarded=std::max(discarded,(total-mapped)/total);
        for(auto& y:massFractions)y.back()/=mapped;
    }
    if(grid.size()<10 || grid.back()-grid.front()>.1)
        throw std::runtime_error("Invalid guess domain");
    location=grid;
    for(auto& x:location)x=(x-grid.front())/(grid.back()-grid.front());
    return discarded;
}
}
