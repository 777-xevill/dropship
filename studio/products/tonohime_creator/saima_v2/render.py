"""Render the two Saima story ads (1080x1920, 30 fps): camera moves on stills, lip-synced talking clips,
whip-cut transitions, kinetic Bangla captions (HTML-rendered), review card, end card, clean audio + SFX.
Usage: render.py [v1|v2]"""
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.io import wavfile

sys.path.insert(0, r"E:\Dropship\studio")
sys.path.insert(0, str(Path(__file__).parent))
from studio.render import Renderer, font_css, data_uri  # noqa: E402
from script import V1, V2  # noqa: E402

HERE = Path(__file__).parent
P = HERE.parent
W, H, FPS, SR = 1080, 1920, 30, 48000
TMP = HERE / "tmp"
TMP.mkdir(exist_ok=True)
FINAL = P / "final" / "saima"
FINAL.mkdir(parents=True, exist_ok=True)

CHAIN = ("highpass=f=90:poles=2,lowpass=f=13000,afftdn=nr=12:nf=-50:tn=1,equalizer=f=3200:t=q:w=1.2:g=2,"
         "acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=3dB,alimiter=limit=0.89:level=false")


# ---------------------------------------------------------------- audio helpers
def wav(p):
    sr, a = wavfile.read(p)
    a = a.astype(np.float32) / (32768.0 if a.dtype == np.int16 else 1.0)
    return a if a.ndim == 1 else a.mean(1)


def clean(src, dst, tempo=1.0):
    af = CHAIN + (f",atempo={tempo:.3f}" if tempo != 1.0 else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", str(SR), "-ac", "1", str(dst)], check=True)
    return dst


def sfx_whoosh():
    d = 0.42; n = int(SR * d); t = np.arange(n) / SR
    rng = np.random.default_rng(3); x = rng.standard_normal(n).astype(np.float32)
    y = np.zeros(n, np.float32); acc = 0.0
    for i in range(n):
        a = 0.03 + 0.45 * (i / n) ** 1.6
        acc += a * (x[i] - acc); y[i] = acc
    y = np.diff(np.concatenate([[0], y]))  # remove low end -> airy
    env = np.sin(np.pi * np.minimum(1, t / d)) ** 2
    y = y * env
    return y / (np.abs(y).max() + 1e-6) * 0.45


def sfx_hit():
    d = 0.6; t = np.arange(int(SR * d)) / SR
    body = np.sin(2 * np.pi * (140 * np.exp(-t * 9) + 70) * t) * np.exp(-t * 7)
    click = np.random.default_rng(5).standard_normal(len(t)) * np.exp(-t * 90) * 0.4
    y = body + click
    return (y / np.abs(y).max() * 0.55).astype(np.float32)


def sfx_ding():
    d = 0.9; t = np.arange(int(SR * d)) / SR
    y = (np.sin(2 * np.pi * 1318.5 * t) * 0.6 + np.sin(2 * np.pi * 1975.5 * t) * 0.35) * np.exp(-t * 5)
    return (y * 0.35).astype(np.float32)


def sfx_riser(d):
    t = np.arange(int(SR * d)) / SR
    noise = np.random.default_rng(9).standard_normal(len(t)).astype(np.float32)
    noise = np.diff(np.concatenate([[0], noise]))
    tone = np.sin(2 * np.pi * (300 + 900 * (t / d) ** 2) * t)
    y = (noise * 0.25 + tone * 0.15) * (t / d) ** 2
    return (y / (np.abs(y).max() + 1e-6) * 0.25).astype(np.float32)


# ---------------------------------------------------------------- image helpers
def cover(im, w, h):
    ih, iw = im.shape[:2]
    s = max(w / iw, h / ih)
    r = cv2.resize(im, (int(iw * s + 0.5), int(ih * s + 0.5)), interpolation=cv2.INTER_LANCZOS4)
    y0, x0 = (r.shape[0] - h) // 2, (r.shape[1] - w) // 2
    return r[y0:y0 + h, x0:x0 + w]


def load(p, focus=(0.5, 0.5), fit=False):
    im = cv2.cvtColor(np.array(Image.open(p).convert("RGB")), cv2.COLOR_RGB2BGR)
    big = cover_focus(im, int(W * 1.25), int(H * 1.25), focus)
    if fit:  # whole photo, centred, on a blurred darkened copy of itself
        big = (cv2.GaussianBlur(big, (0, 0), 40) * 0.55).astype(np.uint8)
        fw = int(W * 1.25 * 0.92); fh = int(im.shape[0] * fw / im.shape[1])
        fg = cv2.resize(im, (fw, fh), interpolation=cv2.INTER_LANCZOS4)
        y0 = (big.shape[0] - fh) // 2 - 60; x0 = (big.shape[1] - fw) // 2
        big[y0:y0 + fh, x0:x0 + fw] = fg
    blur = cv2.GaussianBlur(big, (0, 0), 1.2)
    return cv2.addWeighted(big, 1.6, blur, -0.6, 0)  # unsharp: AI stills are soft once upscaled


def cover_focus(im, w, h, focus):
    ih, iw = im.shape[:2]
    s = max(w / iw, h / ih)
    r = cv2.resize(im, (int(iw * s + 0.5), int(ih * s + 0.5)), interpolation=cv2.INTER_LANCZOS4)
    x0 = int((r.shape[1] - w) * focus[0]); y0 = int((r.shape[0] - h) * focus[1])
    return r[y0:y0 + h, x0:x0 + w]


def ease(x):
    x = min(1, max(0, x)); return 1 - (1 - x) ** 3


def view(src, z, cx, cy):
    """Crop a zoom z (1 = full 1.25x canvas fits) around centre (cx,cy in 0..1) and resize to W,H."""
    sh, sw = src.shape[:2]
    cw, ch = sw / (1.25 * z), sh / (1.25 * z)
    x0 = np.clip(cx * sw - cw / 2, 0, sw - cw); y0 = np.clip(cy * sh - ch / 2, 0, sh - ch)
    M = np.array([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]], np.float32)
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


MOVES = {  # (z0, z1, cx0, cx1, cy0, cy1)
    "crash": None,
    "push": (1.0, 1.14, .5, .5, .5, .47),
    "pull": (1.18, 1.02, .5, .5, .45, .5),
    "pan_r": (1.12, 1.16, .42, .58, .5, .5),
    "pan_l": (1.12, 1.16, .58, .42, .5, .5),
    "rise": (1.12, 1.18, .5, .5, .6, .42),
    "orbit": (1.05, 1.22, .44, .56, .52, .48),
}


def still_frame(src, move, t, d):
    x = t / d
    if move == "crash":   # fast punch-in, then slow creep
        z = 1.0 + 0.22 * ease(x * 6) + 0.06 * x
        cx, cy = .5, .42
    else:
        z0, z1, a0, a1, b0, b1 = MOVES[move]
        e = x * 0.35 + 0.65 * (1 - (1 - x) ** 2)
        z, cx, cy = z0 + (z1 - z0) * e, a0 + (a1 - a0) * e, b0 + (b1 - b0) * e
    return view(src, z, cx, cy)


class Clip:
    def __init__(self, path, start=0.0, blur=0):
        self.cap = cv2.VideoCapture(str(path)); self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.start, self.blur, self.idx, self.last = start, blur, -1, None

    def frame(self, t):
        want = int((self.start + t) * self.fps)
        while self.idx < want:
            ok, f = self.cap.read()
            if not ok:
                break
            self.idx += 1; self.last = f
        f = cover(self.last, W, H)
        if self.blur:
            f = cv2.GaussianBlur(f, (0, 0), self.blur)
        return f


# ---------------------------------------------------------------- overlays (HTML -> RGBA)
CSS = """*{box-sizing:border-box;margin:0}html,body{width:1080px;height:1920px;background:transparent;overflow:hidden}
body{font-family:'Anek Bangla','Hind Siliguri',sans-serif;position:relative;-webkit-font-smoothing:antialiased}.a{position:absolute}"""


def page(body, extra=""):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{font_css()}{CSS}{extra}</style></head><body>{body}</body></html>"


_cache = {}


def overlay(r, key, html):
    if key not in _cache:
        out = TMP / f"{key}.png"
        r.html(html, out, W, H, transparent=True)
        a = np.array(Image.open(out).convert("RGBA")).astype(np.float32) / 255
        rgb = cv2.cvtColor((a[..., :3] * 255).astype(np.uint8), cv2.COLOR_RGB2BGR).astype(np.float32) / 255
        ys, xs = np.where(a[..., 3] > 0.01)
        box = (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1) if len(ys) else (0, 1, 0, 1)
        _cache[key] = (rgb, a[..., 3:4], box)
    return _cache[key]


def comp(frame, ov, alpha=1.0, scale=1.0, dy=0):
    rgb, a, (y0, y1, x0, x1) = ov
    if alpha <= 0:
        return frame
    if scale != 1.0 or dy:
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        M = np.array([[scale, 0, cx - scale * cx], [0, scale, cy - scale * cy + dy]], np.float32)
        rgb = cv2.warpAffine(rgb, M, (W, H)); a = cv2.warpAffine(a, M, (W, H))[..., None]
        y0, y1, x0, x1 = 0, H, 0, W
    f = frame[y0:y1, x0:x1].astype(np.float32) / 255
    aa = a[y0:y1, x0:x1] * alpha
    frame[y0:y1, x0:x1] = ((f * (1 - aa) + rgb[y0:y1, x0:x1] * aa) * 255).astype(np.uint8)
    return frame


def cap_html(words, hi):
    spans = " ".join(f"<span class='w{' on' if i == hi else ''}'>{w}</span>" for i, w in enumerate(words))
    css = (".cap{left:70px;right:70px;top:1330px;text-align:center;font-weight:800;font-size:76px;line-height:1.25;color:#fff;"
           "text-shadow:0 4px 0 #000,0 0 18px rgba(0,0,0,.65);-webkit-text-stroke:3px #000;paint-order:stroke fill}"
           ".w{display:inline-block;padding:0 10px;border-radius:16px}.on{background:#ffd31a;color:#111;-webkit-text-stroke:0;text-shadow:none}")
    return page(f"<div class='a cap'>{spans}</div>", css)


def title_html(text, sub=""):
    css = (".t{left:60px;right:60px;top:210px;text-align:center}.t b{display:inline-block;background:#fff;color:#111;font-weight:800;"
           "font-size:84px;line-height:1.18;padding:18px 34px 26px;border-radius:26px;box-shadow:0 14px 40px rgba(0,0,0,.35)}"
           ".t i{display:block;margin-top:18px;font-style:normal;font-weight:700;font-size:46px;color:#ffd31a;text-shadow:0 3px 10px #000}")
    return page(f"<div class='a t'><b>{text}</b>{f'<i>{sub}</i>' if sub else ''}</div>", css)


def nametag_html():
    css = (".n{left:60px;top:1150px;background:rgba(92,21,32,.92);border:3px solid #e9c9a0;color:#fff;border-radius:999px;"
           "padding:10px 34px 14px;font-size:48px;font-weight:700}.n small{font-size:30px;color:#e9c9a0;font-weight:500;margin-left:10px}")
    return page("<div class='a n'>সাইমা <small>Private Choice BD</small></div>", css)


def num_html(n):
    css = (".c{left:60px;top:200px;width:170px;height:170px;border-radius:50%;background:#ffd31a;color:#111;font-weight:800;"
           "font-size:120px;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 30px rgba(0,0,0,.4);"
           "border:6px solid #fff;line-height:1;padding-top:14px}")
    return page(f"<div class='a c'>{n}</div>", css)


def chips_html(items, top=260):
    chips = "".join(f"<div class='c'>✓ {x}</div>" for x in items)
    css = (f".w{{left:0;right:0;top:{top}px;display:flex;flex-direction:column;align-items:center;gap:22px}}"
           ".c{background:#fff;color:#5c1520;font-weight:800;font-size:62px;padding:14px 40px 20px;border-radius:999px;"
           "box-shadow:0 12px 30px rgba(0,0,0,.35)}")
    return page(f"<div class='a w'>{chips}</div>", css)


def review_html(dark):
    bg, fg, sub = ("#ffffff", "#1b1b1b", "#666") if not dark else ("#3a0a12", "#fff", "#e9c9a0")
    css = (f".r{{left:70px;right:70px;top:560px;background:{bg};color:{fg};border-radius:40px;padding:56px 60px 60px;"
           "box-shadow:0 30px 80px rgba(0,0,0,.45);border:4px solid #e9c9a0}"
           f".h{{display:flex;align-items:center;gap:22px;font-size:40px;font-weight:700;color:{sub}}}"
           ".av{width:96px;height:96px;border-radius:50%;background:#c9a27a;display:flex;align-items:center;justify-content:center;"
           "font-size:52px;color:#fff;font-weight:800;padding-top:6px}"
           ".st{color:#f5b301;font-size:64px;letter-spacing:6px;margin:30px 0 12px;font-family:'Segoe UI Symbol',sans-serif}"
           ".q{font-size:86px;font-weight:800;line-height:1.25}"
           f".f{{margin-top:26px;font-size:38px;color:{sub};font-weight:600}}"
           ".lab{left:0;right:0;top:430px;text-align:center}.lab span{background:#ffd31a;color:#111;font-weight:800;font-size:50px;"
           "padding:10px 34px 16px;border-radius:999px}")
    body = ("<div class='a lab'><span>গ্রাহকের মতামত</span></div>"
            "<div class='a r'><div class='h'><div class='av'>?</div><div>একজন গ্রাহক<br><small>নাম গোপন রাখা হয়েছে</small></div></div>"
            "<div class='st'>★★★★★</div><div class='q'>“জিনিসটা সত্যিই অনেক ভালো!”</div>"
            "<div class='f'>— অর্ডারের পর আমাদের জানিয়েছেন</div></div>")
    return page(body, css)


def end_html(dark):
    bottle = data_uri(P / "work/cutouts/bottle_clear_c2.png")
    bg = ("radial-gradient(ellipse at 50% 40%,#8a2633,#3a0a12 75%)" if dark
          else "radial-gradient(ellipse at 50% 40%,#fff6ee,#ecd3c0 80%)")
    fg, acc = ("#f6e6d2", "#e9c9a0") if dark else ("#5c1520", "#a8705f")
    css = (f"body{{background:{bg}}}.b{{left:0;right:0;top:120px;text-align:center;color:{fg}}}"
           f".b .p{{font-family:'Playfair Display';font-style:italic;font-weight:700;font-size:120px;line-height:1}}"
           f".b .c{{font-family:'Playfair Display';font-size:72px;color:{acc}}}"
           f".im{{left:50%;top:420px;height:760px;transform:translateX(-50%);filter:drop-shadow(0 40px 50px rgba(0,0,0,.45))}}"
           f".cta{{left:0;right:0;top:1240px;text-align:center;color:{fg};font-weight:800;font-size:66px}}"
           ".ph{left:50%;top:1350px;transform:translateX(-50%);background:#ffd31a;color:#111;font-family:'Poppins';font-weight:800;"
           "font-size:96px;padding:18px 56px;border-radius:999px;white-space:nowrap;box-shadow:0 16px 40px rgba(0,0,0,.35)}"
           f".bd{{left:0;right:0;top:1560px;display:flex;justify-content:center;gap:18px;flex-wrap:wrap;padding:0 60px}}"
           f".bd span{{border:3px solid {acc};color:{fg};border-radius:999px;padding:8px 26px 12px;font-size:40px;font-weight:700}}")
    body = (f"<div class='a b'><div class='p'>Private</div><div class='c'>Choice Bd</div></div><img class='a im' src='{bottle}'>"
            "<div class='a cta'>দাম ও অর্ডারের জন্য কল করুন</div><div class='a ph'>01612-237962</div>"
            "<div class='a bd'><span>গোপনীয় প্যাকেট</span><span>পণ্য দেখে টাকা</span><span>ফ্রি ডেলিভারি</span></div>")
    return page(body, css)


def stage_img(dark):
    """Product on a branded stage (still), then moved like a camera orbit."""
    bottle = Image.open(P / "work/cutouts/bottle_clear_c2.png").convert("RGBA")
    cw, ch = int(W * 1.25), int(H * 1.25)
    yy, xx = np.mgrid[0:ch, 0:cw]
    d = np.sqrt(((xx - cw / 2) / cw) ** 2 + ((yy - ch * .45) / ch) ** 2)
    c0, c1 = ((138, 38, 51), (30, 4, 8)) if dark else ((255, 247, 240), (226, 196, 176))
    g = np.clip(d / 0.6, 0, 1)[..., None]
    bg = (np.array(c0) * (1 - g) + np.array(c1) * g).astype(np.uint8)
    im = Image.fromarray(bg, "RGB").convert("RGBA")
    # podium
    pod = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    import PIL.ImageDraw as D
    dr = D.Draw(pod)
    px, py, pw = cw // 2, int(ch * .72), int(cw * .42)
    col = (233, 201, 160, 255) if dark else (255, 255, 255, 255)
    dr.rectangle((px - pw // 2, py, px + pw // 2, py + 260), fill=(200, 162, 122, 255) if dark else (236, 222, 210, 255))
    dr.ellipse((px - pw // 2, py - 60, px + pw // 2, py + 60), fill=col)
    dr.ellipse((px - pw // 2, py + 200, px + pw // 2, py + 320), fill=(200, 162, 122, 255) if dark else (236, 222, 210, 255))
    im.alpha_composite(pod)
    bh = int(ch * .5)
    b = bottle.resize((int(bottle.width * bh / bottle.height), bh), Image.LANCZOS)
    sh = Image.new("RGBA", b.size, (0, 0, 0, 0)); sh.putalpha(b.split()[3].point(lambda v: v * 0.45))
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(30))
    im.alpha_composite(sh, (px - b.width // 2 + 30, py - bh + 40))
    im.alpha_composite(b, (px - b.width // 2, py - bh + 10))
    return cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------- grade
rng = np.random.default_rng(1)
GRAIN = [rng.normal(0, 5.5, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.28 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H * .48) / (H / 2)) ** 2) ** 1.4).clip(0.55, 1).astype(np.float32)[..., None]


def grade(f, i, sweep=None):
    x = f.astype(np.float32)
    x = (x - 128) * 1.06 + 128
    x[..., 2] *= 1.03; x[..., 0] *= 0.98      # a touch warm
    if sweep is not None:                      # light sweep across product shots
        band = np.exp(-((xx - sweep * W * 1.6 + W * .3 + (yy - H / 2) * .35) / 90.0) ** 2)[..., None] * 60
        x += band
    x *= VIG
    g = cv2.resize(GRAIN[i % 6], (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
    return np.clip(x + g, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- build one video
def build(spec, shots, r):
    name = spec["name"]
    lines = dict(spec["lines"])
    # audio: talking-clip lines use the clip's own (lip-synced) voice
    segs, t = [], 0.25
    for sh in shots:
        if "audio" in sh:
            a = wav(sh["audio"])
        elif "line" in sh:
            a = wav(sh["_wav"])
        else:
            a = np.zeros(int(SR * sh["dur"]), np.float32)
        d = max(len(a) / SR + sh.get("pad", 0.08), sh.get("min", 0))
        segs.append((t, a)); sh["t0"], sh["d"] = t, d
        t += d
    shots[0]["t0"], shots[0]["d"] = 0, shots[0]["d"] + 0.25
    total = t
    n = int(total * FPS)
    vo = np.zeros(int(total * SR) + SR, np.float32); fx = np.zeros_like(vo)
    for (s, a) in segs:
        i = int(s * SR); vo[i:i + len(a)] += a
    wh, hit, ding = sfx_whoosh(), sfx_hit(), sfx_ding()

    def put(buf, s, y, g=1.0):
        i = max(0, int(s * SR)); buf[i:i + len(y)] += y[:len(buf) - i] * g
    put(fx, 0.0, hit, 0.9)
    for sh in shots[1:]:
        put(fx, sh["t0"] - 0.2, wh, 0.8)
        if sh.get("ding"):
            put(fx, sh["t0"] + 0.15, ding)
        if sh.get("hit"):
            put(fx, sh["t0"], hit, 0.6)
    end = shots[-1]
    put(fx, end["t0"] - 1.1, sfx_riser(1.1), 0.8)
    mix = vo[:int(total * SR)] + fx[:int(total * SR)] * 0.55
    raw = TMP / f"{name}_mix.wav"
    wavfile.write(raw, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    # two-pass linear loudness to -14 LUFS (no pumping, no raised noise floor = no hum)
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    import json, re
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr).group(0))
    final_wav = TMP / f"{name}_final.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
                    f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                    f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
                    "-ar", str(SR), "-ac", "2", str(final_wav)], check=True)

    # video
    out = FINAL / f"{name}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", str(final_wav), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                          stdin=subprocess.PIPE)
    for sh in shots:
        if sh["kind"] == "still":
            sh["_src"] = load(sh["img"], sh.get("focus", (0.5, 0.5)), sh.get("fit", False))
        elif sh["kind"] == "stage":
            sh["_src"] = stage_img(sh.get("dark", True))
        elif sh["kind"] == "clip":
            sh["_clip"] = Clip(sh["clip"], sh.get("start", 0), sh.get("blur", 0))
        # caption overlays
        sh["_caps"] = []
        txt = lines.get(sh.get("line", ""), sh.get("caption", ""))
        if txt and sh.get("captions", True):
            words = txt.replace("…", "").split()
            chunks = [words[i:i + 3] for i in range(0, len(words), 3)]
            tot = sum(len("".join(c)) for c in chunks)
            acc = 0.0
            for ci, c in enumerate(chunks):
                for wi in range(len(c)):
                    k = f"cap_{name}_{sh['line'] if 'line' in sh else 'x'}_{ci}_{wi}"
                    frac0 = (acc + sum(len(w) for w in c[:wi])) / tot
                    sh["_caps"].append((frac0, overlay(r, k, cap_html(c, wi))))
                acc += len("".join(c))
        sh["_ovs"] = [(overlay(r, f"{name}_{sh_i}_{j}", html), kind) for j, (html, kind) in enumerate(sh.get("ovs", []))
                      for sh_i in [shots.index(sh)]]

    for fi in range(n):
        t = fi / FPS
        k = max(i for i, s in enumerate(shots) if s["t0"] <= t + 1e-6)
        sh = shots[k]; lt = t - sh["t0"]; d = sh["d"]
        if sh["kind"] in ("still", "stage"):
            f = still_frame(sh["_src"], sh["move"], lt, d)
        elif sh["kind"] == "clip":
            f = sh["_clip"].frame(lt)
            if sh.get("zoom"):
                f = view(cv2.resize(f, (int(W * 1.25), int(H * 1.25))), 1.0 + 0.08 * lt / d, .5, .45)
        else:
            f = np.zeros((H, W, 3), np.uint8)
        # whip-in on every cut (except the very first frame of the ad)
        if k > 0 and lt < 0.17:
            s = int(70 * (1 - lt / 0.17)) | 1
            kern = np.zeros((1, s), np.float32); kern[0, :] = 1 / s
            f = cv2.filter2D(f, -1, kern)
            sc = 1.0 + 0.08 * (1 - lt / 0.17)
            f = view(cv2.resize(f, (int(W * 1.25), int(H * 1.25))), sc, .5, .5)
        if k == 0 and lt < 0.12:   # flash on the opening hit
            f = cv2.addWeighted(f, 1 - (0.12 - lt) * 5, np.full_like(f, 255), (0.12 - lt) * 5, 0)
        if sh["kind"] != "end":
            sweep = (lt / d) if sh.get("sweep") else None
            f = grade(f, fi, sweep)
        # shake on hook
        if sh.get("shake") and lt < 0.5:
            a = (0.5 - lt) * 18
            M = np.float32([[1, 0, np.sin(fi * 2.1) * a], [0, 1, np.cos(fi * 1.7) * a]])
            f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        for (ov, kind) in sh["_ovs"]:
            if kind == "pop":
                x = min(1, lt / 0.22); sc = 0.6 + 0.4 * (1 - (1 - x) ** 3) + 0.06 * np.sin(min(1, x) * np.pi)
                f = comp(f, ov, min(1, lt / 0.1), sc)
            elif kind == "slide":
                x = min(1, lt / 0.35); f = comp(f, ov, min(1, lt / 0.15), 1.0, int(260 * (1 - x) ** 3))
            elif kind == "late":
                x = (lt - 0.4) / 0.25
                if x > 0:
                    f = comp(f, ov, min(1, x), 0.85 + 0.15 * min(1, x))
            else:
                f = comp(f, ov)
        if sh["_caps"]:
            frac = (lt - (0.25 if k == 0 else 0)) / max(0.1, d - 0.15)
            cur = [c for c in sh["_caps"] if c[0] <= max(0, frac)]
            if cur:
                f = comp(f, cur[-1][1])
        ff.stdin.write(f.tobytes())
    ff.stdin.close(); ff.wait()
    print("made", out, f"{total:.1f}s")
    return out


def main(which):
    A = HERE / "audio"
    W2 = P / "work"
    # cleaned lip-sync audio for the two talking clips
    b01 = clean(W2 / "audio/b01_8b473cfa6eef_s1.08.wav", TMP / "b01.wav")
    b02 = clean(W2 / "audio/b02_4d42015f16c6_s1.08.wav", TMP / "b02.wav")
    with Renderer() as r:
        if which in ("v1", "all"):
            sp = V1
            for k, _ in sp["lines"]:
                clean(A / f"{k}.wav", TMP / f"{k}.wav", 1.06)
            L = lambda k: dict(line=k, _wav=TMP / f"{k}.wav")  # noqa: E731
            shots = [
                dict(kind="still", img=W2 / "scenes/selfie_b.png", move="crash", shake=True, focus=(.5, .25),
                     ovs=[(title_html("যে জিনিস চাইতে<br>সবাই লজ্জা পায়…"), "pop"), (nametag_html(), "late")], **L("v1_l1")),
                dict(kind="still", img=W2 / "scenes/poster_hero.png", move="push", focus=(.5, .3), **L("v1_l2")),
                dict(kind="stage", dark=True, move="orbit", sweep=True, hit=True,
                     ovs=[(title_html("টোনো হিমে", "পানি-ভিত্তিক লুব্রিকেন্ট জেল"), "pop")], **L("v1_l3")),
                dict(kind="clip", clip=W2 / "clips/talk_selfie-b02_selfie_b_5f16c6_s1.08.mp4", audio=b02, zoom=True,
                     caption="টোনো হিমে আঠালো না, কাপড়ে দাগ পড়ে না, পানিতে সহজে ধুয়ে যায়।", line="b02x"),
                dict(kind="still", img=P / "photos/texture.png", move="push", focus=(.85, .5), **L("v1_l5")),
                dict(kind="still", img=P / "photos/texture.png", move="pull", focus=(.6, .5), ding=True, captions=False,
                     ovs=[(review_html(False), "slide")], **L("v1_l6")),
                dict(kind="still", img=W2 / "scenes/selfie_b.png", move="pan_r", focus=(.5, .7),
                     ovs=[(chips_html(["গোপনীয় প্যাকেট", "পণ্য দেখে টাকা"]), "pop")], **L("v1_l7")),
                dict(kind="end", dark=True, captions=False, min=3.8,
                     ovs=[(end_html(True), "static")], **L("v1_l8")),
            ]
            build(sp, shots, r)
        if which in ("v2", "all"):
            sp = V2
            for k, _ in sp["lines"]:
                clean(A / f"{k}.wav", TMP / f"{k}.wav")
            L = lambda k: dict(line=k, _wav=TMP / f"{k}.wav")  # noqa: E731
            cox = HERE / "coxs_boats.mp4"
            l1 = wav(TMP / "v2_l1.wav"); cut = 1.55   # beach shot, then Saima
            wavfile.write(TMP / "v2_l1a.wav", SR, (l1[:int(cut * SR)] * 32767).astype(np.int16))
            wavfile.write(TMP / "v2_l1b.wav", SR, (l1[int(cut * SR):] * 32767).astype(np.int16))
            shots = [
                dict(kind="clip", clip=cox, start=0.0, shake=True, pad=0.0, line="v2_l1", _wav=TMP / "v2_l1a.wav", captions=False,
                     ovs=[(title_html("কেনার আগে<br>৩টি কথা জানুন"), "pop")]),
                dict(kind="still", img=W2 / "scenes/selfie_a.png", move="crash", line="v2_l1b", _wav=TMP / "v2_l1b.wav",
                     caption="এই জেল কেনার আগে তিনটা কথা জানুন।",
                     ovs=[(title_html("কেনার আগে<br>৩টি কথা জানুন"), "static"), (nametag_html(), "late")]),
                dict(kind="clip", clip=W2 / "clips/talk_selfie-b01_selfie_a_fa6eef_s1.08.mp4", audio=b01, zoom=True,
                     caption="এটা স্বামী-স্ত্রীর ব্যক্তিগত জীবনের স্বস্তির জন্য একটা পানি-ভিত্তিক জেল।", line="b01x",
                     ovs=[(num_html("১"), "pop")]),
                dict(kind="still", img=P / "photos/bottles.png", fit=True, move="push", sweep=True, ovs=[(num_html("২"), "pop")], **L("v2_l3")),
                dict(kind="stage", dark=False, move="orbit", sweep=True,
                     ovs=[(num_html("৩"), "pop"), (chips_html(["গোপনীয় প্যাকেট", "ক্যাশ অন ডেলিভারি"], 1000), "late")], **L("v2_l4")),
                dict(kind="clip", clip=cox, start=1.7, blur=6, ding=True, captions=False, min=3.4,
                     ovs=[(review_html(True), "slide")], line="v2_l5", _wav=TMP / "v2_l56.wav"),
                dict(kind="end", dark=False, captions=False, min=4.0, ovs=[(end_html(False), "static")], **L("v2_l7")),
            ]
            l5, l6 = wav(TMP / "v2_l5.wav"), wav(TMP / "v2_l6.wav")
            wavfile.write(TMP / "v2_l56.wav", SR, (np.concatenate([l5, np.zeros(int(.12 * SR)), l6]) * 32767).astype(np.int16))
            build(sp, shots, r)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
