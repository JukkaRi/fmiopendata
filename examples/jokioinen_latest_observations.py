#!/usr/bin/env python
"""Fetch the latest weather observations for Jokioinen from FMI open data."""
import datetime as dt
import json
import math

from fmiopendata.wfs import download_stored_query


def to_jsonable(obj):
    """Recursively convert datetimes/numpy floats/NaN into JSON-safe types."""
    if isinstance(obj, dict):
        return {
            (key.isoformat() if isinstance(key, dt.datetime) else key): to_jsonable(value)
            for key, value in obj.items()
        }
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if hasattr(obj, "item"):  # numpy scalar (e.g. numpy.float64)
        return to_jsonable(obj.item())
    return obj


end_time = dt.datetime.utcnow()
start_time = end_time - dt.timedelta(hours=1)

start_time = start_time.isoformat(timespec="seconds") + "Z"
end_time = end_time.isoformat(timespec="seconds") + "Z"

obs = download_stored_query(
    "fmi::observations::weather::multipointcoverage",
    args=[
        "place=Jokioinen",
        "starttime=" + start_time,
        "endtime=" + end_time,
    ],
)

with open("jokioinen_latest_observations.json", "w") as f:
    json.dump(to_jsonable(obs.data), f, indent=2)

print("Wrote jokioinen_latest_observations.json")
