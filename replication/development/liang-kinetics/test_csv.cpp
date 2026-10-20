#include "Csv.h"
#include <iostream>

int main() {
    using namespace kinetics_control;
    const std::vector<std::string> fields{
        "x_m","Y_H2","Y_C5H5O(1,3)","Y_C5H5O(2,4)","a\"b",""};
    std::string record;
    for(size_t i=0;i<fields.size();++i) {
        if(i)record+=',';
        record+=csvField(fields[i]);
    }
    if(split(record)!=fields || split(record+"\r")!=fields)
        throw std::runtime_error("Species-header CSV round trip failed");
    if(split("1,2,3")!=std::vector<std::string>{"1","2","3"})
        throw std::runtime_error("Numeric CSV fields changed");
    for(const std::string invalid:{"\"unfinished","\"closed\"tail","un\"quoted"}) {
        bool rejected=false;
        try {split(invalid);}catch(const std::runtime_error&){rejected=true;}
        if(!rejected)throw std::runtime_error("Malformed CSV was accepted");
    }
    std::cout<<"PASS species-header round trip and malformed-input checks\n";
}
