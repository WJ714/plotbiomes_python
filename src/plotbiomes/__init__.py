from .data import (
    BIOME_ORDER,
    load_ricklefs_colors,
    load_whittaker_biomes,
    load_whittaker_polygons,
)
from .geometry import classify_biomes, contains_point, get_outliers, locate_biome
from .mapping import map_outliers
from .plotting import plot_points, whittaker_base_plot

__all__ = [
    "BIOME_ORDER",
    "classify_biomes",
    "contains_point",
    "get_outliers",
    "load_ricklefs_colors",
    "load_whittaker_biomes",
    "load_whittaker_polygons",
    "locate_biome",
    "map_outliers",
    "plot_points",
    "whittaker_base_plot",
]

__version__ = "0.1.0"
