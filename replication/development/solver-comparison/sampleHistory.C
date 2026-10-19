#include "../flame-tracking/trackingCore.H"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <iostream>

int main(int argc, char** argv)
{
    if (argc != 4) return 2;
    std::ifstream manifest(argv[2]);
    if (!manifest.good()) throw std::runtime_error("Cannot open manifest");
    std::ofstream out(argv[3]);
    if (!out.good()) throw std::runtime_error("Cannot open output");
    out << std::setprecision(17);
    out << "time_s,side,marker,level,status,x_m,rho_local,U_local,rho_unburned,window_start_s,window_end_s,samples,density_weighted_m_s\n";
    flameTracking::History histories[4];
    double time; std::string directory;
    while (manifest >> time >> directory)
    {
        const std::string base=std::string(argv[1])+"/"+directory+"/";
        std::ifstream scalar(base+"axisLine_T_rho_OH_p.xy"), vector(base+"axisLine_U.xy");
        if (!scalar.good() || !vector.good()) throw std::runtime_error("Missing samples");
        std::vector<flameTracking::Point> points;
        double x,T,rho,OH,p,vectorX,U,V,W;
        while (scalar >> x >> T >> rho >> OH >> p)
        {
            if (!(vector >> vectorX >> U >> V >> W) || std::abs(vectorX-x)>1e-12)
                throw std::runtime_error("Mismatched sample coordinates");
            points.push_back({x,T,OH,rho,U});
        }
        if (!scalar.eof() || (vector >> vectorX)) throw std::runtime_error("Invalid sample rows");
        if (points.size()!=8000) throw std::runtime_error("Expected 8000 sampled cells");
        int index=0;
        for (bool temperature : {true,false}) for (bool left : {true,false})
        {
            const double level=temperature?780.87224522673557:2e-5;
            const auto sample=flameTracking::sample(points,temperature,level,left,298);
            const auto result=histories[index++].add(time,sample,left,5e-6);
            out << time << ',' << (left?"left":"right") << ',' << (temperature?"T":"OH")
                << ',' << level << ',' << result.status << ',' << sample.x << ',' << sample.rho
                << ',' << sample.U << ',' << sample.freshRho << ',' << result.start << ','
                << result.end << ',' << result.count << ',' << result.weighted << '\n';
        }
    }
    if (!manifest.eof()) throw std::runtime_error("Invalid manifest");
    return 0;
}
