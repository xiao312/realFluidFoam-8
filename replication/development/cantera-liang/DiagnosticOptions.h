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
            else throw std::runtime_error("Unknown diagnostic option: "+item);
        }
        if(seen.empty() || text.back()==',')throw std::runtime_error("Empty diagnostic option");
        if(table2 && !bounded)throw std::runtime_error("takahashi-table2 requires bounded-takahashi");
    }
};
}
