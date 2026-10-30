#include "endpointCoordinate.H"
#include "steadyFlameletTable.H"
#include <iostream>
#include <algorithm>
#include <vector>

int main(int argc, char** argv)
{
    try
    {
        if (argc != 2) throw std::runtime_error("Usage: endpoint-probe ACTUAL_STEADY_TABLE");
        const forgeSteady::Table table(argv[1]);
        const double limit=forgeSteady::endpointRoundoffLimit();
        unsigned refused=0, represented=0;
        const auto mustRefuse = [&](double z, bool enabled)
        {
            try { (void)forgeSteady::endpointCoordinate(z,enabled); }
            catch (const std::runtime_error&) { ++refused; return; }
            throw std::runtime_error("Expected strict/material endpoint refusal");
        };
        for (double z : {-std::numeric_limits<double>::epsilon(),std::nextafter(1.0,2.0)}) mustRefuse(z,false);
        for (double z : {-65*std::numeric_limits<double>::epsilon(),1+65*std::numeric_limits<double>::epsilon(),-1e-8,1+1e-8,std::numeric_limits<double>::quiet_NaN()}) mustRefuse(z,true);
        double maxElementDelta=0;
        for (const double z : {-limit,1+limit})
        {
            const auto coordinate=forgeSteady::endpointCoordinate(z,true);
            const auto state=table.lookup(coordinate.value);
            if (coordinate.raw!=z || std::abs(coordinate.delta)>limit || state.y.empty()) throw std::runtime_error("Coordinate mapping contract failed");
            maxElementDelta=std::max(maxElementDelta,table.elementCoordinateDifference(z,coordinate.value));
            ++represented;
        }
        for (double z : {0.0,0.2,0.5,1.0})
        {
            const auto coordinate=forgeSteady::endpointCoordinate(z,true);
            const auto actual=table.lookup(coordinate.value), expected=table.lookup(z);
            if (coordinate.value!=z || coordinate.delta!=0 || actual.y!=expected.y || actual.temperature!=expected.temperature || actual.heatRelease!=expected.heatRelease) throw std::runtime_error("Interior/endpoint identity changed");
        }
        if (maxElementDelta>limit) throw std::runtime_error("Element coordinate perturbation exceeds fixed bound");
        std::cout<<std::setprecision(17)<<"{\"strictAndMaterialRefusals\":"<<refused<<",\"representedBoundaryControls\":"<<represented<<",\"maxElementCoordinateDelta\":"<<maxElementDelta<<",\"fixedLimit\":"<<limit<<",\"passed\":true,\"physicalQualification\":false}\n";
        return 0;
    }
    catch (const std::exception& error) { std::cerr<<error.what()<<std::endl; return 1; }
}
