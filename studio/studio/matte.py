"""Background removal: product cut-outs (rembg) and person video matting for the green-screen format."""
import subprocess
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

from . import config
from .util import StudioError, run, say, video_info

_sessions: dict = {}
CUT_VERSION = "c2"   # bump when cut-out processing changes, so old cached cut-outs are redone
RVM_URL = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx"


def _rembg(model: str):
    if model not in _sessions:
        from rembg import new_session
        _sessions[model] = new_session(model)
    return _sessions[model]


def cutout(src: Path, out: Path, model: str = "isnet-general-use", margin: int = 12) -> Path:
    """Remove the background of a product (or person) photo -> tight RGBA PNG."""
    if out.exists() and out.stat().st_mtime >= Path(src).stat().st_mtime:
        return out
    from rembg import remove
    im = Image.open(src).convert("RGB")
    rgba = remove(im, session=_rembg(model), post_process_mask=True)
    a = np.array(rgba.split()[-1])
    rgba = _fade_cropped_edges(rgba, a)
    a = np.array(rgba.split()[-1])
    ys, xs = np.where(a > 8)
    if len(xs):
        x0, x1 = max(0, xs.min() - margin), min(rgba.width, xs.max() + margin)
        y0, y1 = max(0, ys.min() - margin), min(rgba.height, ys.max() + margin)
        rgba = rgba.crop((x0, y0, x1, y1))
    out.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(out)
    return out


def _fade_cropped_edges(rgba: Image.Image, a: np.ndarray) -> Image.Image:
    """If the product runs off the edge of the photo, a hard straight cut looks cheap.
    Fade that side out softly so it reads as intentional."""
    h, w = a.shape
    edges = {"bottom": a[-2:, :], "top": a[:2, :], "left": a[:, :2], "right": a[:, -2:]}
    alpha = a.astype(np.float32)
    for side, strip in edges.items():
        if (strip > 128).mean() < 0.18:
            continue
        n = int((h if side in ("top", "bottom") else w) * 0.14)
        ramp = np.linspace(0, 1, n, dtype=np.float32) ** 1.4
        if side == "bottom":
            alpha[-n:, :] *= ramp[::-1, None]
        elif side == "top":
            alpha[:n, :] *= ramp[:, None]
        elif side == "left":
            alpha[:, :n] *= ramp[None, :]
        else:
            alpha[:, -n:] *= ramp[None, ::-1]
    out = rgba.copy()
    out.putalpha(Image.fromarray(alpha.clip(0, 255).astype(np.uint8)))
    return out


def on_white(cut_png: Path, out: Path, size: int = 1024) -> Path:
    """Cut-out centred on white: the cleanest product reference for image-edit models."""
    if out.exists() and out.stat().st_mtime >= cut_png.stat().st_mtime:
        return out
    c = Image.open(cut_png).convert("RGBA")
    c.thumbnail((int(size * .82), int(size * .82)), Image.LANCZOS)
    bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    bg.alpha_composite(c, ((size - c.width) // 2, (size - c.height) // 2))
    bg.convert("RGB").save(out)
    return out


def _rvm_model() -> Path:
    p = config.MODELS / "rvm_mobilenetv3_fp32.onnx"
    if not p.exists():
        say("downloading the video-matting model (15 MB, once)", kind="info")
        urllib.request.urlretrieve(RVM_URL, p)
    return p


def video_matte(clip: Path, out_mask: Path, work_h: int = 960) -> Path:
    """Alpha matte video (grey = person) for a talking clip, using Robust Video Matting on CPU."""
    if out_mask.exists() and out_mask.stat().st_mtime >= clip.stat().st_mtime:
        return out_mask
    import onnxruntime as ort
    info = video_info(clip)
    w, h = info["width"], info["height"]
    sh = min(work_h, h)
    sw = int(round(w * sh / h / 2) * 2)
    sess = ort.InferenceSession(str(_rvm_model()), providers=["CPUExecutionProvider"])
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"scale={sw}:{sh}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{sw}x{sh}",
                            "-r", f"{info['fps']:.5f}", "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "16", "-pix_fmt", "yuv420p", str(out_mask)], stdin=subprocess.PIPE)
    rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    ratio = np.array([min(1.0, 512 / max(sw, sh))], np.float32)
    frame_bytes = sw * sh * 3
    try:
        while True:
            buf = dec.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            src = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3).astype(np.float32) / 255.0
            src = src.transpose(2, 0, 1)[None]
            _fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2],
                                              "r4i": rec[3], "downsample_ratio": ratio})
            enc.stdin.write((np.clip(pha[0, 0], 0, 1) * 255).astype(np.uint8).tobytes())
    finally:
        enc.stdin.close()
        enc.wait()
        dec.wait()
    if enc.returncode != 0 or not out_mask.exists():
        raise StudioError(f"Video matting failed for {clip.name}")
    return out_mask


def chroma_matte(clip: Path, out_mask: Path, color: str = "0x00FF00") -> Path:
    """Alternative for clips filmed on a green backdrop: key the colour out with ffmpeg."""
    run(["ffmpeg", "-y", "-i", clip, "-vf",
         f"colorkey={color}:0.30:0.12,alphaextract,format=gray", "-c:v", "libx264", "-crf", "16",
         "-pix_fmt", "yuv420p", out_mask])
    return out_mask
