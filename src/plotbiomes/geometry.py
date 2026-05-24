from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .data import load_whittaker_polygons


DEFAULT_TEMPERATURE_KEYS = ("temp_c", "temperature", "temp", "mean_annual_temperature")
DEFAULT_PRECIPITATION_KEYS = (
    "precp_cm",
    "precipitation",
    "precip_cm",
    "pp_cm",
    "annual_precipitation",
)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def _as_float(value: Any, label: str) -> float:
    if value is None:
        return math.nan
    if isinstance(value, bool):
        raise ValueError(f"{label} values must be numeric, not bool")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} values must be numeric") from exc


def _pick_key(row: Mapping[str, Any], candidates: Sequence[str], label: str) -> str:
    for key in candidates:
        if key in row:
            return key
    raise ValueError(f"Could not find a {label} column in mapping input")


def _normalize_pairs(
    values: Any,
    *,
    temperature: str | int | None = None,
    precipitation: str | int | None = None,
    index_base: int = 1,
) -> list[tuple[int, Any, float, float]]:
    if hasattr(values, "iloc") and hasattr(values, "columns"):
        columns = list(values.columns)
        if temperature is None:
            temperature = columns[0]
        if precipitation is None:
            precipitation = columns[1]
        pairs = []
        for offset, (index, row) in enumerate(values.iterrows()):
            pairs.append(
                (
                    offset + index_base,
                    index,
                    _as_float(row[temperature], "temperature"),
                    _as_float(row[precipitation], "precipitation"),
                )
            )
        return pairs

    if isinstance(values, Mapping):
        temp_key = temperature if isinstance(temperature, str) else None
        precip_key = precipitation if isinstance(precipitation, str) else None
        if temp_key is None:
            temp_key = _pick_key(values, DEFAULT_TEMPERATURE_KEYS, "temperature")
        if precip_key is None:
            precip_key = _pick_key(values, DEFAULT_PRECIPITATION_KEYS, "precipitation")
        temp_values = list(values[temp_key])
        precip_values = list(values[precip_key])
        if len(temp_values) != len(precip_values):
            raise ValueError("Temperature and precipitation columns have different lengths")
        return [
            (
                offset + index_base,
                offset,
                _as_float(temp, "temperature"),
                _as_float(precip, "precipitation"),
            )
            for offset, (temp, precip) in enumerate(zip(temp_values, precip_values))
        ]

    rows = list(values)
    pairs: list[tuple[int, Any, float, float]] = []
    for offset, row in enumerate(rows):
        if isinstance(row, Mapping):
            temp_key = temperature if isinstance(temperature, str) else None
            precip_key = precipitation if isinstance(precipitation, str) else None
            if temp_key is None:
                temp_key = _pick_key(row, DEFAULT_TEMPERATURE_KEYS, "temperature")
            if precip_key is None:
                precip_key = _pick_key(row, DEFAULT_PRECIPITATION_KEYS, "precipitation")
            temp_value = row[temp_key]
            precip_value = row[precip_key]
        else:
            if len(row) != 2:
                raise ValueError("Each row must contain exactly two values")
            temp_col = 0 if temperature is None else int(temperature)
            precip_col = 1 if precipitation is None else int(precipitation)
            temp_value = row[temp_col]
            precip_value = row[precip_col]
        pairs.append(
            (
                offset + index_base,
                offset,
                _as_float(temp_value, "temperature"),
                _as_float(precip_value, "precipitation"),
            )
        )
    return pairs


def _validate_temperature_precipitation(pairs: Sequence[tuple[int, Any, float, float]]) -> None:
    temperatures = [temp for _, _, temp, precip in pairs if not _is_missing(temp) and not _is_missing(precip)]
    precipitations = [
        precip for _, _, temp, precip in pairs if not _is_missing(temp) and not _is_missing(precip)
    ]
    if not temperatures:
        return

    temp_min, temp_max = min(temperatures), max(temperatures)
    if temp_min < -55 or temp_max > 40:
        raise ValueError(
            "Detected mean annual temperature values outside [-55, 40] C. "
            "Check the column order or whether temperatures need to be divided by 10."
        )

    precip_min, precip_max = min(precipitations), max(precipitations)
    if precip_min < 0 or precip_max > 1200:
        raise ValueError(
            "Detected annual precipitation values outside [0, 1200] cm. "
            "Check the column order or convert precipitation from mm to cm."
        )


def _validate_xy(pairs: Sequence[tuple[int, Any, float, float]]) -> None:
    longitudes = [x for _, _, x, y in pairs if not _is_missing(x) and not _is_missing(y)]
    latitudes = [y for _, _, x, y in pairs if not _is_missing(x) and not _is_missing(y)]
    if not longitudes:
        return
    if min(longitudes) < -180 or max(longitudes) > 180:
        raise ValueError("Longitude values must be between -180 and 180 degrees.")
    if min(latitudes) < -90 or max(latitudes) > 90:
        raise ValueError("Latitude values must be between -90 and 90 degrees.")


def _on_segment(
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    tolerance: float,
) -> bool:
    scale = max(1.0, abs(x1), abs(y1), abs(x2), abs(y2))
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > tolerance * scale:
        return False
    return (
        min(x1, x2) - tolerance <= x <= max(x1, x2) + tolerance
        and min(y1, y2) - tolerance <= y <= max(y1, y2) + tolerance
    )


def contains_point(
    polygon: Sequence[tuple[float, float]],
    point: tuple[float, float],
    *,
    include_boundary: bool = True,
    tolerance: float = 1e-9,
) -> bool:
    x, y = point
    inside = False
    vertices = list(polygon)
    if len(vertices) < 3:
        return False

    x1, y1 = vertices[-1]
    for x2, y2 in vertices:
        if include_boundary and _on_segment(x, y, x1, y1, x2, y2, tolerance=tolerance):
            return True
        if (y1 > y) != (y2 > y):
            x_intersection = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_intersection:
                inside = not inside
        x1, y1 = x2, y2
    return inside


def locate_biome(
    temp_c: float,
    precp_cm: float,
    *,
    include_boundary: bool = True,
) -> str | None:
    if _is_missing(temp_c) or _is_missing(precp_cm):
        return None
    point = (float(temp_c), float(precp_cm))
    for biome, polygon in load_whittaker_polygons().items():
        if contains_point(polygon, point, include_boundary=include_boundary):
            return biome
    return None


def classify_biomes(
    tp: Any,
    *,
    validate: bool = True,
    as_dataframe: bool = False,
    index_base: int = 1,
    temperature: str | int | None = None,
    precipitation: str | int | None = None,
) -> list[dict[str, Any]]:
    pairs = _normalize_pairs(
        tp,
        temperature=temperature,
        precipitation=precipitation,
        index_base=index_base,
    )
    if validate:
        _validate_temperature_precipitation(pairs)

    rows = []
    for row_idx, input_index, temp_c, pp_cm in pairs:
        rows.append(
            {
                "row_idx": row_idx,
                "input_index": input_index,
                "temp": temp_c,
                "pp_cm": pp_cm,
                "biome": locate_biome(temp_c, pp_cm),
            }
        )
    return _maybe_dataframe(rows, as_dataframe)


def get_outliers(
    tp: Any,
    *,
    validate: bool = True,
    as_dataframe: bool = False,
    index_base: int = 1,
    temperature: str | int | None = None,
    precipitation: str | int | None = None,
) -> list[dict[str, Any]]:
    pairs = _normalize_pairs(
        tp,
        temperature=temperature,
        precipitation=precipitation,
        index_base=index_base,
    )
    if validate:
        _validate_temperature_precipitation(pairs)

    outliers = _outlier_rows_from_pairs(pairs)
    return _maybe_dataframe(outliers, as_dataframe)


def _outlier_rows_from_pairs(pairs: Sequence[tuple[int, Any, float, float]]) -> list[dict[str, Any]]:
    outliers = []
    for row_idx, input_index, temp_c, pp_cm in pairs:
        if _is_missing(temp_c) or _is_missing(pp_cm):
            continue
        if locate_biome(temp_c, pp_cm) is None:
            outliers.append(
                {
                    "row_idx": row_idx,
                    "input_index": input_index,
                    "temp": temp_c,
                    "pp_cm": pp_cm,
                }
            )
    return outliers


def _maybe_dataframe(rows: list[dict[str, Any]], as_dataframe: bool):
    if not as_dataframe:
        return rows
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "DataFrame output requires pandas. "
            "Install with `pip install plotbiomes-python[dataframe]`."
        ) from exc
    return pd.DataFrame(rows)
