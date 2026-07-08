"""Azure Function App exposing the Harmonie surface forecast grid as JSON over an ASGI-hosted FastAPI app."""
import datetime as dt
import math

import azure.functions as func
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse

from fmiopendata.wfs import download_stored_query

fastapi_app = FastAPI(
    title="FMI Harmonie Grid API",
    description="Fetch Harmonie surface forecast grid data for a bounding box and date range.",
    version="1.0.0",
)


def to_jsonable(obj):
    """Recursively convert datetimes/numpy arrays/NaN into JSON-safe types."""
    if isinstance(obj, dict):
        return {str(key): to_jsonable(value) for key, value in obj.items()}
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


@fastapi_app.get("/", include_in_schema=False)
def root():
    """Redirect the bare root URL to the Swagger UI."""
    return RedirectResponse(url="/docs")


@fastapi_app.get("/grid")
def get_grid(
    x1: float = Query(..., description="Minimum longitude of the bounding box"),
    y1: float = Query(..., description="Minimum latitude of the bounding box"),
    x2: float = Query(..., description="Maximum longitude of the bounding box"),
    y2: float = Query(..., description="Maximum latitude of the bounding box"),
    start_date: dt.date = Query(..., description="Start date (UTC)"),
    end_date: dt.date = Query(..., description="End date (UTC)"),
    parameters: str = Query(
        "Temperature,WindSpeedMS",
        description="Comma-separated list of parameters to fetch. Leaving this too broad "
                     "over a large bbox can produce a very large response.",
    ),
):
    """Fetch the latest Harmonie surface forecast grid for a bounding box and date range."""
    if x1 >= x2 or y1 >= y2:
        raise HTTPException(status_code=400, detail="x1 must be < x2 and y1 must be < y2")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")

    bbox = f"{x1},{y1},{x2},{y2}"
    start_time = dt.datetime.combine(start_date, dt.time.min).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = dt.datetime.combine(end_date, dt.time.max).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        model_data = download_stored_query(
            "fmi::forecast::harmonie::surface::grid",
            args=[
                "starttime=" + start_time,
                "endtime=" + end_time,
                "bbox=" + bbox,
                "parameters=" + parameters,
            ],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to query FMI open data: {exc}") from exc

    if not model_data.data:
        raise HTTPException(status_code=404, detail="No model data available for the given date range")

    # Take the latest model run and parse its GRIB payload into numpy arrays
    latest_init_time = max(model_data.data.keys())
    grid = model_data.data[latest_init_time]
    grid.parse(delete=True)

    return to_jsonable(
        {
            "init_time": latest_init_time,
            "start_time": grid.start_time,
            "end_time": grid.end_time,
            "bbox": bbox,
            "latitudes": grid.latitudes,
            "longitudes": grid.longitudes,
            "data": grid.data,
        }
    )


app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
