"""Brand palette: taken from project.yaml (brand.colors.primary) or picked from the product's own colours."""
import colorsys
from pathlib import Path

import numpy as np
from PIL import Image


def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, round(c)))) for c in rgb)


def _rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _with_l(rgb, l, s_min=None):
    h, _l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    if s_min is not None:
        s = max(s, s_min)
    return _hex(tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s)))


def dominant(cutout: Path) -> str:
    """Most 'brand-like' colour of a product cut-out: frequent AND saturated."""
    im = Image.open(cutout).convert("RGBA")
    im.thumbnail((240, 240))
    a = np.asarray(im).reshape(-1, 4).astype(np.float32)
    px = a[a[:, 3] > 200][:, :3]
    if len(px) < 50:
        return "#1f6f5c"
    hls = np.array([colorsys.rgb_to_hls(*(p / 255)) for p in px[:: max(1, len(px) // 4000)]])
    keep = (hls[:, 2] > 0.28) & (hls[:, 1] > 0.12) & (hls[:, 1] < 0.88)
    if keep.sum() < 30:
        return "#1f6f5c"
    hues = hls[keep, 0]
    hist, edges = np.histogram(hues, bins=24, range=(0, 1), weights=hls[keep, 2])
    b = int(np.argmax(hist))
    sel = hls[keep][(hues >= edges[b]) & (hues < edges[b + 1])]
    h, l, s = np.median(sel[:, 0]), np.median(sel[:, 1]), np.median(sel[:, 2])
    return _hex(tuple(c * 255 for c in colorsys.hls_to_rgb(h, l, s)))


def palette(primary: str | None = None, cutout: Path | None = None) -> dict:
    base = _rgb(primary) if primary else _rgb(dominant(cutout) if cutout else "#1f6f5c")
    return {
        "primary": _with_l(base, 0.40, s_min=0.45),
        "dark": _with_l(base, 0.17, s_min=0.35),
        "mid": _with_l(base, 0.62, s_min=0.35),
        "light": _with_l(base, 0.93, s_min=0.30),
        "accent": "#FFE14D",
    }
