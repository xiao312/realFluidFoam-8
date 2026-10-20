#pragma once
#include <sstream>
#include <stdexcept>
#include <string>
#include <set>
namespace liang {
struct DiagnosticOptions {
    bool dense=false,bounded=false,pressureChemistry=false,fineGrid=false;
    bool smoothedAlpha=false;
    bool table2=false;
    bool highTemperature=false;
    bool bulkTakahashi=false,massGradient=false;
    bool nonidealDriving=false;
    bool totalEnthalpy=false,pureSpeciesFlux=false;
    explicit DiagnosticOptions(const std::string& text) {
        if(text=="full")return;
        std::stringstream stream(text);std::string item;std::set<std::string> seen;
        while(std::getline(stream,item,',')) {
            if(!seen.insert(item).second)throw std::runtime_error("Repeated diagnostic option");
            if(item=="dense-increment")dense=true;
            else if(item=="bounded-takahashi")bounded=true;
            else if(item=="pressure-chemistry")pressureChemistry=true;
            else if(item=="fine-grid")fineGrid=true;
            else if(item=="smoothed-alpha")smoothedAlpha=true;
            else if(item=="takahashi-table2")table2=true;
            else if(item=="takahashi-high-t")highTemperature=true;
            else if(item=="takahashi-bulk")bulkTakahashi=true;
            else if(item=="mass-gradient")massGradient=true;
            else if(item=="nonideal-driving")nonidealDriving=true;
            else if(item=="total-enthalpy")totalEnthalpy=true;
            else if(item=="pure-species-flux")pureSpeciesFlux=true;
            else throw std::runtime_error("Unknown diagnostic option: "+item);
        }
        if(seen.empty() || text.back()==',')throw std::runtime_error("Empty diagnostic option");
        if(table2 && !bounded)throw std::runtime_error("takahashi-table2 requires bounded-takahashi");
        if(highTemperature && !(bounded && table2))throw std::runtime_error("takahashi-high-t requires bounded-takahashi,takahashi-table2");
        if(bulkTakahashi && !(bounded && table2))throw std::runtime_error("takahashi-bulk requires bounded-takahashi,takahashi-table2");
        if(pureSpeciesFlux && !totalEnthalpy)throw std::runtime_error("pure-species-flux requires total-enthalpy");
        if(nonidealDriving && (massGradient || totalEnthalpy))
            throw std::runtime_error("nonideal-driving requires the stock energy and mole-gradient formulations");
    }
};
}
