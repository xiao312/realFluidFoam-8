#include "../../development/cantera-liang/StagedTransport.h"
#include "cantera/base/Solution.h"
#include "cantera/transport/TransportFactory.h"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>

// Read-only prescribed-state evaluation through the same adapter used by flames.
// An ideal phase avoids SRK phase/root selection in correlation-only checks.
int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::runtime_error(
            "Usage: property-probe INPUTS REQUESTS.csv corrected|legacy");
        const std::string input = argv[1], mode = argv[3];
        if (mode != "corrected" && mode != "legacy") throw std::runtime_error("Invalid mode");
        std::ifstream table(input + "/species.txt");
        std::vector<liang::Species> parameters;
        std::vector<std::string> names;
        liang::Species parameter; std::string name;
        while (table >> name >> parameter.Tc >> parameter.Pc >> parameter.Vc
                     >> parameter.W >> parameter.omega >> parameter.eos) {
            parameters.push_back(parameter); names.push_back(name);
        }
        if (names.size() != 53) throw std::runtime_error("Expected 53 species");
        Cantera::TransportFactory::factory()->reg("liang-staged", [&]() {
            auto* transport = new liang::StagedTransport;
            transport->parameters = parameters;
            transport->boundedTakahashi = true;
            transport->table2 = mode == "corrected";
            return transport;
        });
        auto solution = Cantera::newSolution(input + "/ideal.yaml", "", "liang-staged");
        auto gas = solution->thermo();
        auto* transport = dynamic_cast<liang::StagedTransport*>(solution->transport().get());
        if (!transport) throw std::runtime_error("Wrong transport adapter");
        const size_t n = gas->nSpecies();
        for (size_t k = 0; k < n; ++k) {
            if (gas->speciesName(k) != names[k]) throw std::runtime_error("Species order mismatch");
        }
        std::ifstream requests(argv[2]); std::string line;
        if (!std::getline(requests, line)) throw std::runtime_error("Missing requests");
        std::cout << "row,D4_m2_s,D5_m2_s,factor,max_mix_relative_error,symmetry_relative_error,actual_Pr,actual_Tr\n"
                  << std::setprecision(17);
        size_t row = 0;
        while (std::getline(requests, line)) {
            std::stringstream record(line); std::vector<std::string> fields; std::string field;
            while (std::getline(record, field, ',')) fields.push_back(field);
            if (fields.size() != 9) throw std::runtime_error("Invalid request width");
            const size_t i = gas->speciesIndex(fields[0]), j = gas->speciesIndex(fields[1]);
            if (i >= n || j >= n || i == j) throw std::runtime_error("Invalid species pair");
            const double fraction = std::stod(fields[2]);
            std::vector<double> x(n, 0), y(n), dilute(n*n), dense(n*n), mixture(n);
            x[i] = fraction; x[j] = 1-fraction;
            gas->setState_TPX(std::stod(fields[3]), std::stod(fields[4]), x.data());
            gas->getMassFractions(y.data());
            transport->stage = 4; transport->getBinaryDiffCoeffs(n, dilute.data());
            transport->stage = 5; transport->getBinaryDiffCoeffs(n, dense.data());
            transport->getMixDiffCoeffs(mixture.data());
            double error = 0, symmetry = 0;
            for (size_t k = 0; k < n; ++k) {
                double denominator = 0;
                for (size_t l = 0; l < n; ++l) {
                    const double d = dense[k+n*l];
                    if (!(d > 0 && std::isfinite(d))) throw std::runtime_error("Invalid Dij");
                    if (l != k) denominator += x[l]/d;
                    symmetry = std::max(symmetry, std::abs(d-dense[l+n*k])/d);
                }
                const double reconstructed = (1-y[k])/denominator;
                error = std::max(error, std::abs(reconstructed-mixture[k])/mixture[k]);
            }
            const double d4 = dilute[i+n*j], d5 = dense[i+n*j];
            const double tc = fraction*parameters[i].Tc + (1-fraction)*parameters[j].Tc;
            const double pc = fraction*parameters[i].Pc + (1-fraction)*parameters[j].Pc;
            std::cout << row++ << ',' << d4 << ',' << d5 << ',' << d5/d4
                      << ',' << error << ',' << symmetry << ',' << gas->pressure()/pc
                      << ',' << gas->temperature()/tc << '\n';
        }
        if (!row) throw std::runtime_error("No property requests");
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 2;
    }
}
