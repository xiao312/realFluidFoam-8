"""Check independently measured axis ticks through the Figure 1 transform."""
from plot import CALIBRATION, figure1_point

rect = CALIBRATION["image_rect_points"]
size = CALIBRATION["image_size_px"]
largest = 0.0
count = 0
for quantity in ["density", "conductivity"]:
    for i, suffix in enumerate(["_x", "_y"]):
        axis = CALIBRATION["calibration"][quantity+suffix]
        for tick in axis["ticks"]:
            values = [500., 100. if quantity == "density" else .05]
            values[i] = tick["value"]
            point = figure1_point(quantity, *values)
            expected = rect[i]+tick["pixel"]*(rect[i+2]-rect[i])/size[i]
            largest = max(largest, abs(point[i]-expected))
            count += 1
assert count >= 15
assert largest < .2, largest
print(f"PASS {count} Figure 1 ticks; maximum residual {largest:.6g} PDF points")
