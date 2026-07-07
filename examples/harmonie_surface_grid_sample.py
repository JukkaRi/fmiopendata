#!/usr/bin/env python
"""Fetch a grid-based sample of Harmonie surface forecast data from FMI open data."""
import datetime as dt
import json
import math

import numpy as np

from fmiopendata.wfs import download_stored_query


def to_jsonable(obj):
    """Recursively convert datetimes/numpy arrays/NaN into JSON-safe types."""
    if isinstance(obj, dict):
        return {
            (key.isoformat() if isinstance(key, dt.datetime) else str(key)): to_jsonable(value)
            for key, value in obj.items()
        }
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist())
    if isinstance(obj, list):
        return [to_jsonable(item) for item in obj]
    if isinstance(obj, dt.datetime):
        return obj.isoformat()
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if hasattr(obj, "item"):  # numpy scalar (e.g. numpy.float64)
        return to_jsonable(obj.item())
    return obj


# Limit the time
now = dt.datetime.utcnow()
# Depending on the current time and availability of the model data, adjusting
# the hours below might be necessary to get any data
start_time = now.strftime("%Y-%m-%dT00:00:00Z")
end_time = now.strftime("%Y-%m-%dT18:00:00Z")

# Small bounding box (Helsinki area) and a couple of parameters, to keep the
# sample grid a reasonable size. Widening the bbox or dropping "parameters"
# will pull the full model domain, which is on the order of hundreds of MB.
model_data = download_stored_query(
    "fmi::forecast::harmonie::surface::grid",
    args=[
        "starttime=" + start_time,
        "endtime=" + end_time,
        "bbox=24,59,26,61",
        "parameters=Temperature,WindSpeedMS",
    ],
)

# Take the latest model run and parse its GRIB payload into numpy arrays
latest_init_time = max(model_data.data.keys())
grid = model_data.data[latest_init_time]
grid.parse(delete=True)

sample = {
    "init_time": latest_init_time,
    "start_time": grid.start_time,
    "end_time": grid.end_time,
    "latitudes": grid.latitudes,
    "longitudes": grid.longitudes,
    "data": grid.data,
}

with open("harmonie_surface_grid_sample.json", "w") as f:
    json.dump(to_jsonable(sample), f, indent=2)

print("Wrote harmonie_surface_grid_sample.json")
