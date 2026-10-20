#pragma once
#include <stdexcept>
#include <string>
#include <vector>

namespace kinetics_control {
// One physical record per line: embedded newlines are not profile identifiers.
inline std::string csvField(const std::string& value) {
    if(value.find_first_of("\r\n")!=std::string::npos)
        throw std::runtime_error("CSV field contains a newline");
    if(value.find_first_of(",\"")==std::string::npos)return value;
    std::string result="\"";
    for(char c:value) {
        result+=c;
        if(c=='"')result+='"';
    }
    return result+'"';
}

inline std::vector<std::string> split(const std::string& input) {
    std::string line=input;
    if(!line.empty() && line.back()=='\r')line.pop_back();
    std::vector<std::string> fields;
    size_t i=0;
    for(;;) {
        std::string field;
        if(i<line.size() && line[i]=='"') {
            ++i;bool closed=false;
            while(i<line.size()) {
                char c=line[i++];
                if(c!='"') {field+=c;continue;}
                if(i<line.size() && line[i]=='"') {field+='"';++i;continue;}
                closed=true;break;
            }
            if(!closed || (i<line.size() && line[i]!=','))
                throw std::runtime_error("Malformed quoted CSV field");
        } else {
            while(i<line.size() && line[i]!=',') {
                if(line[i]=='"')throw std::runtime_error("Quote inside unquoted CSV field");
                field+=line[i++];
            }
        }
        if(field.find_first_of("\r\n")!=std::string::npos)
            throw std::runtime_error("CSV field contains a newline");
        fields.push_back(field);
        if(i==line.size())break;
        ++i;
    }
    return fields;
}
}
