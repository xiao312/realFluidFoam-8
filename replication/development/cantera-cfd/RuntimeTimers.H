#ifndef RF_CANTERA_RUNTIME_TIMERS_H
#define RF_CANTERA_RUNTIME_TIMERS_H
#include <chrono>
#include <fstream>
#include <iomanip>
#include <map>
#include <string>

class RuntimeTimers {
    using Clock=std::chrono::steady_clock;
    bool enabled_;
    std::map<std::string,Clock::time_point> starts_;
    std::map<std::string,double> totals_;
public:
    explicit RuntimeTimers(const Foam::fvMesh& mesh) {
        Foam::IOdictionary config(Foam::IOobject("canteraBridge",mesh.time().constant(),mesh,
            Foam::IOobject::MUST_READ,Foam::IOobject::NO_WRITE,false));
        enabled_=config.lookupOrDefault<bool>("runtimeProfiling",false);
    }
    void start(const std::string& name) {if(enabled_)starts_[name]=Clock::now();}
    void stop(const std::string& name) {
        if(enabled_)totals_[name]+=std::chrono::duration<double>(Clock::now()-starts_.at(name)).count();
    }
    void write(const Foam::Time& time) {
        if(!enabled_)return;
        std::ofstream out((time.path()/"cantera-runtime.csv").c_str(),std::ios::app);
        if(!out)FatalErrorInFunction << "Cannot write runtime timings" << Foam::exit(Foam::FatalError);
        for(const auto& item:totals_)
            out<<std::setprecision(16)<<time.value()<<','<<item.first<<','<<item.second<<'\n';
        totals_.clear();
    }
};
#endif
