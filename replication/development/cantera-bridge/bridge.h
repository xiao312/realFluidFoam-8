#ifndef RF_CANTERA_BRIDGE_H
#define RF_CANTERA_BRIDGE_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct rf_ct_context rf_ct_context;
typedef struct {
    double density, enthalpy, cp, conductivity, viscosity, molecular_weight;
} rf_ct_properties;
/* Caller owns all buffers. Context owns its model and error-message storage.
 * A null create result leaves an explanatory, terminated string in error.
 * Other calls return 0 on success, 1 on failure; query rf_ct_error(context).
 * n must equal rf_ct_species_count(context); all species arrays have n entries.
 * partial_enthalpies and mass_sources may be null to skip those calculations.
 * Units and nonideal enthalpy conventions are specified in README.md. */
rf_ct_context* rf_ct_create(const char* inputs,int stage,const char* options,
                            char* error,size_t error_capacity);
void rf_ct_destroy(rf_ct_context* context);
size_t rf_ct_species_count(const rf_ct_context* context);
int rf_ct_species_name(rf_ct_context* context,size_t index,char* name,size_t capacity);
/* Species molecular weight in kg/kmol; required caller-owned output. */
int rf_ct_species_weight(rf_ct_context* context,size_t index,double* weight);
const char* rf_ct_error(const rf_ct_context* context);
int rf_ct_evaluate(rf_ct_context* context,double temperature,double pressure,
                   const double* mass_fractions,size_t n,rf_ct_properties* properties,
                   double* partial_enthalpies,double* diffusion,double* mass_sources);
/* Closed adiabatic constant-pressure reactor. Fresh TPY and t=0 on every call.
 * Both output buffers are required; final_mass_fractions has n entries.
 * Outputs are valid only on success. No CFD source normalization is implied. */
int rf_ct_advance_cp(rf_ct_context* context,double temperature,double pressure,
                     const double* mass_fractions,size_t n,double duration,
                     double relative_tolerance,double absolute_tolerance,
                     double* final_temperature,double* final_mass_fractions);
#ifdef __cplusplus
}
#endif
#endif
