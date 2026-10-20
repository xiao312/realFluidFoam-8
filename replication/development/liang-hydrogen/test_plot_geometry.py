"""Check renderer coordinates against independently extracted original ticks."""
import json
from pathlib import Path
import numpy as np
from plot import AXES, FIGURE7, axis, figure7_coordinates

reference = json.loads(Path(__file__).with_name("figure7-calibration.json").read_text())
checks = [
    ("x_ticks", "value_cm", "center_x_pt", "x_points_per_cm", "x_intercept_points"),
    ("T_ticks", "value_K", "center_y_pt", "temperature_points_per_K",
     "temperature_intercept_points"),
    ("X_ticks", "log10_mole_fraction", "center_y_pt",
     "log_species_points_per_decade", "log_species_intercept_points"),
]
errors = []
for key, value, coordinate, slope, intercept in checks:
    for tick in reference[key]:
        errors.append(abs(FIGURE7[slope]*tick[value]+FIGURE7[intercept]-tick[coordinate]))
assert max(errors) < .01, max(errors)
# A physical 5-micrometre separation must cover one original horizontal tick.
positions = figure7_coordinates(np.array([0., 5e-6]), np.array([1500., 2000.]))
ticks = reference["x_ticks"]
assert abs((positions[1]-positions[0])-(ticks[1]["center_x_pt"]-ticks[0]["center_x_pt"])) < .01
other_errors = {}
for name, reference_axis in AXES.items():
    error = max(abs(axis(name, value)-point) for value, point in
                zip(reference_axis["values"], reference_axis["page_points"]))
    assert error < (.12 if name.startswith("6_") else .02), (name, error)
    other_errors[name] = error
assert abs(axis("4_x", .6)-272.693) < .02
print(json.dumps({"independent_ticks": len(errors), "max_error_pt": max(errors),
                  "five_micrometres_pt": positions[1]-positions[0],
                  "figures_2_6_axis_residuals_pt": other_errors}))
