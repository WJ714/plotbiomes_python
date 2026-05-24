from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .geometry import (
    _normalize_pairs,
    _outlier_rows_from_pairs,
    _pick_key,
    _validate_temperature_precipitation,
    _validate_xy,
)

LONGITUDE_KEYS = ("longitude", "lon", "x", "easting")
LATITUDE_KEYS = ("latitude", "lat", "y", "northing")


def _normalize_xy_pairs(
    xy: Any,
    *,
    longitude: str | int | None,
    latitude: str | int | None,
    index_base: int,
):
    if isinstance(xy, Mapping):
        lon_key = longitude if isinstance(longitude, str) else None
        lat_key = latitude if isinstance(latitude, str) else None
        if lon_key is None:
            lon_key = _pick_key(xy, LONGITUDE_KEYS, "longitude")
        if lat_key is None:
            lat_key = _pick_key(xy, LATITUDE_KEYS, "latitude")
        return _normalize_pairs(xy, temperature=lon_key, precipitation=lat_key, index_base=index_base)
    return _normalize_pairs(xy, temperature=longitude, precipitation=latitude, index_base=index_base)


def map_outliers(
    tp: Any,
    xy: Any,
    *,
    validate: bool = True,
    tiles: str = "OpenStreetMap",
    zoom_start: int = 2,
    index_base: int = 1,
    longitude: str | int | None = None,
    latitude: str | int | None = None,
    **map_kwargs: Any,
) -> Any:
    try:
        import folium
    except ImportError as exc:
        raise ImportError(
            "map_outliers requires folium. Install with `pip install plotbiomes-python[map]`."
        ) from exc

    tp_pairs = _normalize_pairs(tp, index_base=index_base)
    xy_pairs = _normalize_xy_pairs(
        xy,
        longitude=longitude,
        latitude=latitude,
        index_base=index_base,
    )
    if len(tp_pairs) != len(xy_pairs):
        raise ValueError("xy and tp must have the same number of rows")
    if not xy_pairs:
        raise ValueError("xy and tp must contain at least one row")

    if validate:
        _validate_temperature_precipitation(tp_pairs)
        _validate_xy(xy_pairs)

    outliers = _outlier_rows_from_pairs(tp_pairs)

    xy_by_row = {row_idx: (lon, lat) for row_idx, _, lon, lat in xy_pairs}
    coordinates = [
        xy_by_row[row["row_idx"]]
        for row in outliers
        if row["row_idx"] in xy_by_row
    ]
    if not coordinates:
        coordinates = [(lon, lat) for _, _, lon, lat in xy_pairs]

    lon_center = sum(lon for lon, _ in coordinates) / len(coordinates)
    lat_center = sum(lat for _, lat in coordinates) / len(coordinates)
    fmap = folium.Map(
        location=[lat_center, lon_center],
        tiles=tiles,
        zoom_start=zoom_start,
        **map_kwargs,
    )

    for row in outliers:
        lon_lat = xy_by_row.get(row["row_idx"])
        if lon_lat is None:
            continue
        lon, lat = lon_lat
        popup = (
            f"row_idx: {row['row_idx']}<br>"
            f"temp: {row['temp']:.3f} C<br>"
            f"precip: {row['pp_cm']:.3f} cm"
        )
        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.8,
            popup=folium.Popup(popup, max_width=260),
        ).add_to(fmap)
    return fmap
