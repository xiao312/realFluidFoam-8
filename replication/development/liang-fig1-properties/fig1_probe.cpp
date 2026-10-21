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
//
// Exit status: 0 complete sweep, 2 dimensional/unit self-check failed, 3 incomplete
// coverage (any rejected temperature, or fewer rows than requested).
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>
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

// The SRK kernel is kmol-based, so liang::R is J/(kmol K); the Shomate fit above is
// J/(mol K).  The dimensionless Cp/R that Ely-Hanley needs and that the cpR_ideal
// column reports therefore requires an explicit factor 1000.  Omitting it is silent --
// the number stays finite and merely 1000 times too small -- so the conversion is
// pinned twice: once on the gas constant itself and once on a value of Cp/R whose
// magnitude is known independently (O2 near 300 K, Cp/R = 3.53).
constexpr double R_KMOL_REFERENCE = 8314.462618;   // J/(kmol K), CODATA 2018
constexpr double CP_R_O2_300K = 3.53;              // dimensionless, Shomate at 300 K
constexpr double CP_R_MOLAR_TO_KMOL = 1000.0;      // J/(mol K) -> J/(kmol K)

// Audited window for the ideal-gas Cp/R of O2 between 150 K and 1000 K: 3.46 at
// 150 K, 3.53 at 300 K, 3.75 at 600 K, 4.03 at 1000 K.  Anything outside this band is
// a units or fit defect, not a physical state, so it is rejected by name.
constexpr double CP_R_O2_MIN = 3.30;
constexpr double CP_R_O2_MAX = 4.20;

double cp_ideal(double T) {
    const double t = T / 1000.0;
    const double *c = T < 700.0 ? SHOMATE_LOW : SHOMATE_HIGH;
    return c[0] + c[1] * t + c[2] * t * t + c[3] * t * t * t + c[4] / (t * t);
}

// Dimless Cp/R from the ideal-gas Cp in J/(mol K), using the kmol-based R of the kernel.
double cp_over_R(double cp_molar_J_molK) {
    return CP_R_MOLAR_TO_KMOL * cp_molar_J_molK / liang::R;
}

void require_finite(double value, const char *name) {
    if (!std::isfinite(value)) throw std::runtime_error(std::string("non-finite ") + name);
}

}  // namespace

int main(int argc, char **argv) {
    double Tmin = 150.0, Tmax = 1000.0, step = 1.0;
    if (argc == 4) {
        Tmin = std::atof(argv[1]);
        Tmax = std::atof(argv[2]);
        step = std::atof(argv[3]);
    }
    // Dimensional canary: the kernel's gas constant must be the kmol-based one, because
    // cp_over_R above converts J/(mol K) into its units.
    if (!(std::fabs(liang::R - R_KMOL_REFERENCE) < 1e-4)) {
        std::fprintf(stderr, "unit_check liang::R %.9f is not J/(kmol K) as assumed\n",
                     static_cast<double>(liang::R));
        return 2;
    }
    // Independent magnitude check that the conversion is applied exactly once: the
    // ideal-gas Cp/R of O2 at 300 K is 3.53, so 0.00353 or 3530 both fail here.
    const double cp_R_300K = cp_over_R(cp_ideal(300.0));
    if (!(std::fabs(cp_R_300K - CP_R_O2_300K) < 0.05)) {
        std::fprintf(stderr, "unit_check Cp/R(300 K) %.6f deviates from %.6f by more than 0.05\n",
                     cp_R_300K, CP_R_O2_300K);
        return 2;
    }
    std::fprintf(stderr, "unit_check R %.6f J/(kmol K) Cp/R(300 K) %.4f\n",
                 static_cast<double>(liang::R), cp_R_300K);

    const std::vector<liang::Species> srk = {{TC_O2, PC_O2, VC_O2, W_O2, OMEGA_O2}};
    const std::vector<double> x = {1.0};
    const long expected = static_cast<long>(std::floor((Tmax - Tmin) / step + 1e-9)) + 1;
    long written = 0, rejected = 0;
    std::printf("# Liang et al. 2019 Fig. 1, pure O2, p = 100 atm = %.1f Pa\n", P_FIG1);
    std::printf("# SRK volume from SrkKernel.h, residual cp from SRK enthalpy, lambda from ElyHanley.H,\n");
    std::printf("# ideal-gas cp from the NIST Shomate fit (ranges joined at 700 K)\n");
    std::printf("T_K,rho_srk_kg_m3,Z_srk,v_srk_m3_kmol,cp_ideal_J_molK,cp_res_J_molK,cp_J_molK,"
                "lambda_eh_W_mK,cpR_ideal\n");
    for (double T = Tmin; T <= Tmax + 1e-9; T += step) {
        try {
            const auto z = liang::evaluate(T, P_FIG1, x, srk);
            const double cp_i = cp_ideal(T);
            const double cp_R = cp_over_R(cp_i);
            if (!(CP_R_O2_MIN <= cp_R && cp_R <= CP_R_O2_MAX)) {
                throw std::domain_error("ideal Cp/R outside the audited O2 window [3.30,4.20]");
            }
            const double cp_res = z.cp / 1000.0;             // J/kmol/K -> J/mol/K
            const double rho = W_O2 / z.v;
            const double Z = P_FIG1 * z.v / (liang::R * T);
            const std::vector<rfElyHanley::Species> eh = {
                {TC_O2, PC_O2, VC_O2, W_O2, OMEGA_O2, cp_R}};
            const std::vector<double> X = {1.0}, Vbar = {z.v};
            const double lambda = rfElyHanley::conductivity(T, z.v, eh, X, Vbar);
            require_finite(cp_i, "cp_ideal");
            require_finite(cp_res, "cp_res");
            require_finite(rho, "rho");
            require_finite(Z, "Z");
            require_finite(lambda, "lambda");
            std::printf("%.4f,%.6f,%.6f,%.8f,%.6f,%.6f,%.6f,%.8f,%.6f\n",
                        T, rho, Z, z.v, cp_i, cp_res, cp_i + cp_res, lambda, cp_R);
            ++written;
        } catch (const std::exception &error) {
            // Keep the sweep alive and leave the rejected state on stderr; the row is
            // omitted rather than filled with a substituted value.  Any rejection makes
            // the process exit nonzero below, so a silent gap cannot be reported as a
            // successful run.
            std::fprintf(stderr, "rejected_T %.4f %s\n", T, error.what());
            ++rejected;
        }
    }
    // Explicit join report for the Shomate splice at 700 K.
    const double lo = cp_ideal(700.0 - 1e-6), hi = cp_ideal(700.0 + 1e-6);
    std::fprintf(stderr, "shomate_join_700K %.9f %.9f rel_jump %.3e\n", lo, hi, (hi - lo) / lo);
    std::fprintf(stderr, "coverage rows %ld expected %ld rejected %ld\n", written, expected, rejected);
    if (written == 0 || rejected > 0 || written != expected) {
        std::fprintf(stderr, "coverage_fail the sweep is incomplete; no result may be reported\n");
        return 3;
    }
    return 0;
}
