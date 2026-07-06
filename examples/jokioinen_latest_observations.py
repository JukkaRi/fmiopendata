#!/usr/bin/env python
"""Fetch the latest weather observations for Jokioinen from FMI open data."""
import datetime as dt

from fmiopendata.wfs import download_stored_query

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

latest_time = max(obs.data.keys())
for station, params in obs.data[latest_time].items():
    print(f"{station} @ {latest_time}")
    for name, obs_value in params.items():
        print(f"  {name}: {obs_value['value']} {obs_value['units']}")
