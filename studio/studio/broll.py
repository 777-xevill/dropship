"""B-roll segments rendered frame by frame (smooth sub-pixel motion), no AI and no GPU needed."""
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import FPS, H, W
from .util import StudioError


class _Writer:
    def __init__(self, out: Path):
        self.out = out
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
             "-r", str(FPS), str(out)], stdin=subprocess.PIPE)

    def put(self, im: Image.Image):
        if im.mode != "RGB":
            im = im.convert("RGB")
        self.p.stdin.write(im.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()
        if self.p.returncode != 0:
            raise StudioError(f"ffmpeg failed writing {self.out.name}")


def _ease_out_back(t: float) -> float:
    c1, c3 = 1.4, 2.4
    t = min(1.0, max(0.0, t))
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def cover(im: Image.Image, w: int, h: int) -> Image.Image:
    r = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * r)), max(h, round(im.height * r))), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def kenburns(src: Path, dur: float, out: Path, seed: int = 0, zoom: float = 0.09, layout: str = "full") -> Path:
    """Slow push-in or pull-out with a gentle drift."""
    rnd = random.Random(seed)
    big = cover(Image.open(src).convert("RGB"), int(W * 1.18), int(H * 1.18))
    n = max(1, round(dur * FPS))
    zin = rnd.random() < 0.6
    dx, dy = rnd.uniform(-1, 1) * W * 0.03, rnd.uniform(-1, 1) * H * 0.02
    wr = _Writer(out)
    for k in range(n):
        t = _ease(k / max(1, n - 1))
        z = 1.0 + zoom * (t if zin else 1 - t)
        cw, ch = big.width / 1.18 / z, big.height / 1.18 / z
        cx = big.width / 2 + dx * (t - .5) + 3 * math.sin(k / FPS * 1.7)
        cy = big.height / 2 + dy * (t - .5) + 2 * math.sin(k / FPS * 1.3 + 1)
        wr.put(big.resize((W, H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)))
    wr.close()
    return out


LAYOUTS = {  # where b-roll subjects sit, per video format (fractions of the frame height)
    "full": {"cy": 0.43, "max_h": 0.40, "card_cy": 0.45, "card_h": 0.56},
    "gs": {"cy": 0.35, "max_h": 0.28, "card_cy": 0.35, "card_h": 0.38},   # green-screen: creator owns the bottom
}


def photo_card(src: Path, dur: float, out: Path, seed: int = 0, layout: str = "full") -> Path:
    """A real photo as a rounded card over a blurred copy of itself (keeps any aspect ratio honest)."""
    lay = LAYOUTS[layout]
    im = Image.open(src).convert("RGB")
    bg = cover(im, W, H).filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * .55))
    cw = int(W * 0.84)
    chh = min(int(H * lay["card_h"]), round(im.height * cw / im.width))
    if round(im.height * cw / im.width) > chh:
        cw = round(im.width * chh / im.height)
    card = cover(im, cw, chh)
    mask = Image.new("L", (cw, chh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw, chh), 44, fill=255)
    shadow = Image.new("RGBA", (cw + 120, chh + 120), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((60, 75, 60 + cw, 75 + chh), 44, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(26))
    n = max(1, round(dur * FPS))
    wr = _Writer(out)
    for k in range(n):
        t = k / max(1, n - 1)
        s = 0.94 + 0.06 * _ease_out_back(min(1, t * 3.2)) + 0.025 * t
        frame = bg.copy().convert("RGBA")
        cwk, chk = round(cw * s), round(chh * s)
        c = card.resize((cwk, chk), Image.BILINEAR)
        m = mask.resize((cwk, chk), Image.BILINEAR)
        sh = shadow.resize((round(shadow.width * s), round(shadow.height * s)), Image.BILINEAR)
        cy = int(H * lay["card_cy"] - chk / 2)
        frame.alpha_composite(sh, ((W - sh.width) // 2, cy - round(60 * s)))
        frame.paste(c, ((W - cwk) // 2, cy), m)
        wr.put(frame)
    wr.close()
    return out


def product_stage(cut: Path, stage: Path, dur: float, out: Path, seed: int = 0, scale: float = 0.66,
                  layout: str = "full") -> Path:
    """Product cut-out on a branded stage: pop-in, float, slow turn, one light sweep."""
    lay = LAYOUTS[layout]
    rnd = random.Random(seed)
    bg0 = Image.open(stage).convert("RGBA").resize((W, H))
    prod = Image.open(cut).convert("RGBA")
    pw = int(W * scale)
    ph = round(prod.height * pw / prod.width)
    if ph > H * lay["max_h"]:
        ph = int(H * lay["max_h"])
        pw = round(prod.width * ph / prod.height)
    prod = prod.resize((pw, ph), Image.LANCZOS)
    alpha = prod.split()[-1]
    # contact shadow
    sh = Image.new("RGBA", (pw + 200, 160), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((100, 40, 100 + pw, 120), fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    # light sweep band
    band = Image.new("L", (pw * 3, ph), 0)
    bd = ImageDraw.Draw(band)
    for i in range(60):
        v = int(110 * (1 - abs(i - 30) / 30))
        bd.line([(pw + i * 4, 0), (pw + i * 4 - ph // 2, ph)], fill=v, width=5)
    band = band.filter(ImageFilter.GaussianBlur(12))
    sweep_t0 = rnd.uniform(0.25, 0.4)
    rot_dir = rnd.choice([-1, 1])
    n = max(1, round(dur * FPS))
    cy0 = int(H * lay["cy"])
    wr = _Writer(out)
    for k in range(n):
        t = k / max(1, n - 1)
        sec = k / FPS
        z = 1.0 + 0.035 * t
        bw, bh = W / z, H / z
        frame = bg0.resize((W, H), Image.BILINEAR, box=((W - bw) / 2, (H - bh) / 2, (W + bw) / 2, (H + bh) / 2))
        s = 0.86 + 0.14 * _ease_out_back(min(1.0, sec / 0.5))
        ang = rot_dir * (1.6 * math.sin(sec * 0.9))
        p = prod
        if 0 <= t - sweep_t0 <= 0.45:
            off = int((t - sweep_t0) / 0.45 * pw * 2)
            hl = band.crop((pw * 2 - off, 0, pw * 3 - off, ph))
            light = Image.new("RGBA", (pw, ph), (255, 255, 255, 0))
            light.putalpha(Image.fromarray(np.minimum(np.asarray(hl), np.asarray(alpha))))
            p = prod.copy()
            p.alpha_composite(light)
        p = p.resize((max(1, round(pw * s)), max(1, round(ph * s))), Image.BILINEAR).rotate(ang, Image.BICUBIC, expand=True)
        y = cy0 + int(12 * math.sin(sec * 2.1)) - p.height // 2
        shw = sh.resize((max(1, round(sh.width * s)), sh.height), Image.BILINEAR)
        frame.alpha_composite(shw, ((W - shw.width) // 2, cy0 + round(ph * s) // 2 - 30))
        frame.alpha_composite(p, ((W - p.width) // 2, y))
        wr.put(frame)
    wr.close()
    return out


def still(card: Path, dur: float, out: Path, zoom: float = 0.03) -> Path:
    """A finished full-frame card (end card) with a slow push-in."""
    im = Image.open(card).convert("RGB").resize((W, H))
    n = max(1, round(dur * FPS))
    wr = _Writer(out)
    for k in range(n):
        z = 1.0 + zoom * _ease(k / max(1, n - 1))
        bw, bh = W / z, H / z
        wr.put(im.resize((W, H), Image.BILINEAR, box=((W - bw) / 2, (H - bh) / 2, (W + bw) / 2, (H + bh) / 2)))
    wr.close()
    return out
