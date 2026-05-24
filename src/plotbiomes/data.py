from __future__ import annotations

import csv
from collections import OrderedDict
from functools import lru_cache
from importlib.resources import files
from typing import Any


BIOME_ORDER: tuple[str, ...] = (
    "Tundra",
    "Boreal forest",
    "Temperate seasonal forest",
    "Temperate rain forest",
    "Tropical rain forest",
    "Tropical seasonal forest/savanna",
    "Subtropical desert",
    "Temperate grassland/desert",
    "Woodland/shrubland",
)


def _resource(name: str):
    return files("plotbiomes").joinpath("data", name)


@lru_cache(maxsize=1)
def load_ricklefs_colors() -> "OrderedDict[str, str]":
    with _resource("ricklefs_colors.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return OrderedDict((row["biome"], row["color"]) for row in reader)


@lru_cache(maxsize=1)
def _whittaker_biome_rows() -> tuple[dict[str, Any], ...]:
    rows = []
    with _resource("whittaker_biomes.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                {
                    "temp_c": float(row["temp_c"]),
                    "precp_cm": float(row["precp_cm"]),
                    "biome_id": int(row["biome_id"]),
                    "biome": row["biome"],
                }
            )
    return tuple(rows)


def load_whittaker_biomes(*, as_dataframe: bool = False):
    rows = [dict(row) for row in _whittaker_biome_rows()]
    if not as_dataframe:
        return rows

    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "load_whittaker_biomes(as_dataframe=True) requires pandas. "
            "Install with `pip install plotbiomes-python[dataframe]`."
        ) from exc
    return pd.DataFrame(rows, columns=["temp_c", "precp_cm", "biome_id", "biome"])


@lru_cache(maxsize=1)
def load_whittaker_polygons() -> "OrderedDict[str, tuple[tuple[float, float], ...]]":
    grouped: "OrderedDict[str, list[tuple[float, float]]]" = OrderedDict()
    for row in _whittaker_biome_rows():
        grouped.setdefault(row["biome"], []).append((row["temp_c"], row["precp_cm"]))

    ordered: "OrderedDict[str, tuple[tuple[float, float], ...]]" = OrderedDict()
    for biome in BIOME_ORDER:
        if biome in grouped:
            ordered[biome] = tuple(grouped[biome])
    return ordered
