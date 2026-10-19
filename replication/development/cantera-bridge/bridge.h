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
const char* rf_ct_error(const rf_ct_context* context);
int rf_ct_evaluate(rf_ct_context* context,double temperature,double pressure,
                   const double* mass_fractions,size_t n,rf_ct_properties* properties,
                   double* partial_enthalpies,double* diffusion,double* mass_sources);
#ifdef __cplusplus
}
#endif
#endif
