// Pure-oxygen properties for Liang et al. (2019) Fig. 1 at 100 atm.
//
// Density and residual caloric properties come from the Soave-Redlich-Kwong kernel in
// ../cantera-liang/SrkKernel.h (molar SI: kmol, m3, K, Pa, J); thermal conductivity
// comes from the Ely-Hanley correlation in ../liang-properties/ElyHanley.H.  Both
// headers belong to this repository and need no Cantera SDK, so the figure numbers can
// be reproduced from source alone.  Ideal-gas Cp is the NIST Shomate fit of O2, the
// same coefficients used by ../oxygen-properties/oxygen_properties.py, and the 700 K
// join of the two ranges is written out so the splice can be checked.
//
// Usage: fig1-probe [Tmin Tmax step]      (default 150 1000 1, Kelvin)
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <vector>

#include "../cantera-liang/SrkKernel.h"
#include "../liang-properties/ElyHanley.H"

namespace {

// Liang et al. (2019) Fig. 1: pure oxygen at 100 atm.
constexpr double P_ATM = 101325.0;
constexpr double P_FIG1 = 100.0 * P_ATM;
constexpr double TC_O2 = 154.581;    // K
constexpr double PC_O2 = 5.043e6;    // Pa
constexpr double VC_O2 = 0.0734;     // m3/kmol
constexpr double W_O2 = 31.9988;     // kg/kmol
constexpr double OMEGA_O2 = 0.022;

// NIST Shomate Cp of O2, J/(mol K); lower range 100-700 K, upper range 700-6000 K.
constexpr double SHOMATE_LOW[5] = {31.32234, -20.23531, 57.86644, -36.50624, -0.007374};
constexpr double SHOMATE_HIGH[5] = {30.03235, 8.772972, -3.988133, 0.788313, -0.741599};

double cp_ideal(double T) {
    const double t = T / 1000.0;
    const double *c = T < 700.0 ? SHOMATE_LOW : SHOMATE_HIGH;
    return c[0] + c[1] * t + c[2] * t * t + c[3] * t * t * t + c[4] / (t * t);
}

}  // namespace

int main(int argc, char **argv) {
    double Tmin = 150.0, Tmax = 1000.0, step = 1.0;
    if (argc == 4) {
        Tmin = std::atof(argv[1]);
        Tmax = std::atof(argv[2]);
        step = std::atof(argv[3]);
    }
    const std::vector<liang::Species> srk = {{TC_O2, PC_O2, VC_O2, W_O2, OMEGA_O2}};
    const std::vector<double> x = {1.0};
    std::printf("# Liang et al. 2019 Fig. 1, pure O2, p = 100 atm = %.1f Pa\n", P_FIG1);
    std::printf("# SRK volume from SrkKernel.h, residual cp from SRK enthalpy, lambda from ElyHanley.H,\n");
    std::printf("# ideal-gas cp from the NIST Shomate fit (ranges joined at 700 K)\n");
    std::printf("T_K,rho_srk_kg_m3,Z_srk,v_srk_m3_kmol,cp_ideal_J_molK,cp_res_J_molK,cp_J_molK,"
                "lambda_eh_W_mK,cpR_ideal\n");
    for (double T = Tmin; T <= Tmax + 1e-9; T += step) {
        try {
            const auto z = liang::evaluate(T, P_FIG1, x, srk);
            const double cp_i = cp_ideal(T);
            const double cp_res = z.cp / 1000.0;             // J/kmol/K -> J/mol/K
            const std::vector<rfElyHanley::Species> eh = {
                {TC_O2, PC_O2, VC_O2, W_O2, OMEGA_O2, cp_i / liang::R}};
            const std::vector<double> X = {1.0}, Vbar = {z.v};
            const double lambda = rfElyHanley::conductivity(T, z.v, eh, X, Vbar);
            std::printf("%.4f,%.6f,%.6f,%.8f,%.6f,%.6f,%.6f,%.8f,%.6f\n",
                        T, W_O2 / z.v, P_FIG1 * z.v / (liang::R * T), z.v, cp_i, cp_res, cp_i + cp_res,
                        lambda, cp_i / liang::R);
        } catch (const std::exception &error) {
            // Keep the sweep alive and leave the rejected state on stderr; the row is
            // omitted rather than filled with a substituted value.
            std::fprintf(stderr, "rejected_T %.4f %s\n", T, error.what());
        }
    }
    // Explicit join report for the Shomate splice at 700 K.
    const double lo = cp_ideal(700.0 - 1e-6), hi = cp_ideal(700.0 + 1e-6);
    std::fprintf(stderr, "shomate_join_700K %.9f %.9f rel_jump %.3e\n", lo, hi, (hi - lo) / lo);
    return 0;
}
