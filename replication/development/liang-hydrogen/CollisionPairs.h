#pragma once
#include "../cantera-liang/LightSpeciesSoret.h"
#include <algorithm>
#include <array>
#include <fstream>
#include <set>
#include <sstream>
#include <string>

namespace hydrogen {
struct CollisionPair {
    std::string first,second;
    std::array<std::array<double,4>,3> coefficients;
};

inline std::pair<std::string,std::string> pairKey(std::string first,std::string second) {
    if(second<first)std::swap(first,second);
    return {first,second};
}

inline std::vector<CollisionPair> parseCollisionPairs(std::istream& input) {
    std::vector<CollisionPair> result;
    std::set<std::pair<std::string,std::string>> seen;
    std::string line;
    while(std::getline(input,line)) {
        if(line.find_first_not_of(" \t\r")==std::string::npos)continue;
        std::istringstream stream(line);CollisionPair pair;
        if(!(stream>>pair.first>>pair.second))
            throw std::runtime_error("Missing collision-pair names");
        for(auto& ratio:pair.coefficients)for(auto& value:ratio)
            if(!(stream>>value) || !std::isfinite(value))
                throw std::runtime_error("Truncated or nonfinite collision-pair coefficients");
        std::string extra;
        if(stream>>extra)throw std::runtime_error("Extra collision-pair fields");
        if(!seen.insert(pairKey(pair.first,pair.second)).second)
            throw std::runtime_error("Duplicate unordered collision pair");
        result.push_back(pair);
    }
    if(result.size()!=10)throw std::runtime_error("Expected ten author collision pairs");
    return result;
}

inline std::vector<CollisionPair> readCollisionPairs(const std::string& path) {
    std::ifstream input(path);
    if(!input)throw std::runtime_error("Manual author Soret requires collision-pairs.txt");
    return parseCollisionPairs(input);
}

inline liang::CollisionRatios evaluateCollisionPair(const CollisionPair& pair,double temperature) {
    if(!(temperature>0 && std::isfinite(temperature)))
        throw std::runtime_error("Invalid author collision temperature");
    const double t=std::log(temperature);
    std::array<double,3> values;
    for(size_t ratio=0;ratio<3;ratio++) {
        const auto& c=pair.coefficients[ratio];
        values[ratio]=c[0]+t*(c[1]+t*(c[2]+t*c[3]));
        if(!(values[ratio]>0 && std::isfinite(values[ratio])))
            throw std::runtime_error("Nonpositive author collision ratio");
    }
    return {values[0],values[1],values[2]};
}
}
