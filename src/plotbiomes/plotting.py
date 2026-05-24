from __future__ import annotations

import warnings
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any

from .data import BIOME_ORDER, load_ricklefs_colors, load_whittaker_polygons
from .geometry import _normalize_pairs


def _matplotlib():
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch, Polygon
    except ImportError as exc:
        raise ImportError(
            "Plotting requires matplotlib. Install with `pip install plotbiomes-python`."
        ) from exc
    return plt, Patch, Polygon


def _normalize_palette(color_palette: Mapping[str, str] | Sequence[str] | None) -> OrderedDict[str, str]:
    default = load_ricklefs_colors()
    if color_palette is None:
        return OrderedDict(default)
    if isinstance(color_palette, Mapping):
        missing = [biome for biome in BIOME_ORDER if biome not in color_palette]
        if missing:
            raise ValueError(f"Missing colors for biomes: {', '.join(missing)}")
        return OrderedDict((biome, str(color_palette[biome])) for biome in BIOME_ORDER)

    colors = list(color_palette)
    if len(colors) != len(BIOME_ORDER):
        raise ValueError(f"Expected {len(BIOME_ORDER)} colors, got {len(colors)}")
    warnings.warn(
        "Unnamed color_palette received; assigning colors in Ricklefs biome order.",
        stacklevel=2,
    )
    return OrderedDict(zip(BIOME_ORDER, colors))


def _matplotlib_color(color: str) -> str:
    lower = color.lower()
    if lower.startswith(("gray", "grey")) and lower[4:].isdigit():
        value = int(lower[4:])
        if 0 <= value <= 100:
            return f"#{value * 255 // 100:02x}{value * 255 // 100:02x}{value * 255 // 100:02x}"
    return color


def whittaker_base_plot(
    *,
    ax: Any = None,
    color_palette: Mapping[str, str] | Sequence[str] | None = None,
    figsize: tuple[float, float] = (8.0, 6.0),
    legend: bool = True,
    edgecolor: str = "gray98",
    linewidth: float = 1.0,
    alpha: float = 1.0,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    aspect: str | float | None = None,
    label_biomes: bool = False,
) -> Any:
    plt, Patch, Polygon = _matplotlib()
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)

    palette = _normalize_palette(color_palette)
    polygons = load_whittaker_polygons()
    legend_handles = []
    mpl_edgecolor = _matplotlib_color(edgecolor)

    for biome in BIOME_ORDER:
        points = polygons[biome]
        patch = Polygon(
            points,
            closed=True,
            facecolor=palette[biome],
            edgecolor=mpl_edgecolor,
            linewidth=linewidth,
            alpha=alpha,
        )
        ax.add_patch(patch)
        ax.update_datalim(points)
        legend_handles.append(Patch(facecolor=palette[biome], edgecolor=mpl_edgecolor, label=biome))

        if label_biomes:
            xs = [x for x, _ in points]
            ys = [y for _, y in points]
            ax.text(sum(xs) / len(xs), sum(ys) / len(ys), biome, ha="center", va="center", fontsize=8)

    ax.autoscale_view()
    ax.set_xlabel(r"Temperature ($^\circ\mathrm{C}$)")
    ax.set_ylabel("Precipitation (cm)")
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)
    if aspect is not None:
        ax.set_aspect(aspect)
    if legend:
        ax.legend(handles=legend_handles, title="Whittaker biomes", frameon=True)
    return ax


def plot_points(
    tp: Any,
    *,
    ax: Any = None,
    base: bool = True,
    temperature: str | int | None = None,
    precipitation: str | int | None = None,
    index_base: int = 1,
    scatter_kwargs: Mapping[str, Any] | None = None,
    **base_kwargs: Any,
) -> Any:
    plt, _, _ = _matplotlib()
    if ax is None and base:
        ax = whittaker_base_plot(**base_kwargs)
    elif ax is None:
        _, ax = plt.subplots(figsize=base_kwargs.pop("figsize", (8.0, 6.0)))
    elif base:
        whittaker_base_plot(ax=ax, **base_kwargs)

    pairs = _normalize_pairs(
        tp,
        temperature=temperature,
        precipitation=precipitation,
        index_base=index_base,
    )
    xs = [temp for _, _, temp, precip in pairs]
    ys = [precip for _, _, temp, precip in pairs]
    kwargs = {
        "s": 36,
        "marker": "o",
        "facecolors": "black",
        "edgecolors": _matplotlib_color("gray95"),
        "linewidths": 0.8,
        "alpha": 0.65,
    }
    if scatter_kwargs:
        kwargs.update(scatter_kwargs)
    ax.scatter(xs, ys, **kwargs)
    return ax
