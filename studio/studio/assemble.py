"""Assemble finished 9:16 videos from lines, clips, b-roll, captions, titles and music.

Formats
  selfie       like ugc2: the character talks to camera holding the product; product b-roll cut-ins.
  greenscreen  like ugc1: full-screen product b-roll, the character cut out in the bottom-right, title on top.
  faceless     no character on screen: product b-roll + her voice-over + captions (needs no GPU at all).
Every hook = one variant. The body is rendered once and reused, so 10 variants cost little extra time.
"""
import os
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from . import broll, captions, config
from .config import FPS, H, W
from .util import StudioError, duration, run, sha

GAP = 0.10                   # silence between lines
TEMPLATE_LETTER = {"selfie": "B", "greenscreen": "G", "faceless": "C"}
CAPTION_Y = {"selfie": 1300, "greenscreen": 1000, "faceless": 1310}   # above Reels' bottom UI, below the product
HEAD_H, HEAD_RIGHT_BLEED = 930, 40
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-video_track_timescale", "15360", "-an"]


def frames(sec: float) -> int:
    return max(1, round(sec * FPS))


# ---------------- visual segments (cached by content) ----------------
def seg_talk(clip: Path, dur: float, cache: Path, zoom: float = 1.0) -> Path:
    n = frames(dur)
    out = cache / f"talk_{sha(clip, n, zoom)}.mp4"
    if out.exists():
        return out
    sh = int(round(H * zoom / 2) * 2)
    vf = (f"scale=-2:{sh}:flags=lanczos,crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.35,setsar=1,fps={FPS},"
          f"eq=contrast=1.03:saturation=1.05,tpad=stop_mode=clone:stop_duration=3")
    run(["ffmpeg", "-y", "-i", clip, "-vf", vf, "-frames:v", n, *ENC, out])
    return out


def seg_greenscreen(bg: Path, clip: Path, mask: Path, dur: float, cache: Path) -> Path:
    n = frames(dur)
    out = cache / f"gs_{sha(bg, clip, mask, n)}.mp4"
    if out.exists():
        return out
    fc = (f"[1:v]scale=-2:{HEAD_H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration=3[fg];"
          f"[2:v]scale=-2:{HEAD_H}:flags=bicubic,fps={FPS},format=gray,tpad=stop_mode=clone:stop_duration=3[m];"
          f"[fg][m]alphamerge[head];[0:v]tpad=stop_mode=clone:stop_duration=3[b];"
          f"[b][head]overlay=x=W-w+{HEAD_RIGHT_BLEED}:y=H-h:format=auto,setsar=1[v]")
    run(["ffmpeg", "-y", "-i", bg, "-i", clip, "-i", mask, "-filter_complex", fc, "-map", "[v]",
         "-frames:v", n, *ENC, out])
    return out


def seg_broll(kind: str, src: Path, dur: float, cache: Path, res: dict, seed: int, layout: str = "full") -> Path:
    n = frames(dur)
    stage = res["stage_gs"] if layout == "gs" else res["stage"]
    out = cache / f"{kind}_{sha(src, n, seed, stage, layout)}.mp4"
    if out.exists():
        return out
    d = n / FPS
    if kind == "product":
        broll.product_stage(src, stage, d, out, seed=seed, layout=layout)
    elif kind == "photo":
        broll.photo_card(src, d, out, seed=seed, layout=layout)
    elif kind == "scene":
        broll.kenburns(src, d, out, seed=seed, layout=layout)
    elif kind == "end":
        broll.still(src, d, out)
    else:
        raise StudioError(f"unknown b-roll kind {kind}")
    return out


def _resolve_visual(visual: str, pj: dict, res: dict, idx: int, filler: bool = False) -> tuple[str, Path]:
    """'product' | 'photo:<file>' | 'scene:<name>' -> (kind, path).
    filler=True: the line has no visual of its own (e.g. green-screen background), so rotate through
    product cards, real photos and 'use_*' scenes to keep the b-roll varied."""
    v = (visual or "product").strip()
    if v.startswith("photo:"):
        p = pj["_dir"] / v.split(":", 1)[1].strip()
        if p.exists():
            return "photo", p
    if v.startswith("scene:"):
        p = res["scenes"].get(v.split(":", 1)[1].strip())
        if p and Path(p).exists():
            return "scene", Path(p)
    cuts = res["cutouts"][:3]
    if not filler:
        return "product", cuts[idx % len(cuts)]
    pool = [("product", c) for c in cuts]
    pool += [("photo", p) for p in res.get("photos_for_broll", [])]
    pool += [("scene", Path(p)) for k, p in sorted(res["scenes"].items()) if k.startswith("use") and Path(p).exists()]
    return pool[idx % len(pool)]


# ---------------- audio ----------------
def _read_wav(p: Path) -> np.ndarray:
    sr, a = wavfile.read(p)
    if sr != 48000:
        raise StudioError(f"{p.name}: expected 48 kHz audio")
    a = a.astype(np.float32) / (32768.0 if a.dtype == np.int16 else 1.0)
    return a if a.ndim == 1 else a.mean(axis=1)


def _whoosh(path: Path) -> Path:
    if path.exists():
        return path
    sr, d = 48000, 0.45
    t = np.linspace(0, d, int(sr * d), False)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(len(t)).astype(np.float32)
    # moving band-pass: cumulative smoothing with a sweeping coefficient
    out = np.zeros_like(noise)
    y = 0.0
    for i, x in enumerate(noise):
        a = 0.04 + 0.5 * (i / len(t)) ** 1.5
        y += a * (x - y)
        out[i] = y
    env = np.sin(np.pi * np.minimum(1, t / d)) ** 2
    out = out * env
    out = out / (np.abs(out).max() + 1e-6) * 0.5
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, sr, (out * 32767).astype(np.int16))
    return path


def build_audio(timeline: list[dict], total: float, out_dir: Path, music: Path | None, sfx: bool) -> Path:
    sr = 48000
    vo = np.zeros(int(total * sr) + sr, np.float32)
    fx = np.zeros_like(vo)
    whoosh = _read_wav(_whoosh(config.ASSETS / "sfx" / "whoosh.wav")) if sfx else None
    for seg in timeline:
        a = _read_wav(seg["audio"])
        s = int(seg["start"] * sr)
        vo[s:s + len(a)] += a[: max(0, len(vo) - s)]
        if whoosh is not None and seg.get("whoosh"):
            ws = max(0, s - int(0.18 * sr))
            fx[ws:ws + len(whoosh)] += whoosh[: max(0, len(fx) - ws)] * 0.35
    vo = vo[: int(total * sr)]
    fx = fx[: int(total * sr)]
    vo_p, fx_p = out_dir / "vo.wav", out_dir / "fx.wav"
    wavfile.write(vo_p, sr, (np.clip(vo, -1, 1) * 32767).astype(np.int16))
    wavfile.write(fx_p, sr, (np.clip(fx, -1, 1) * 32767).astype(np.int16))
    mix = out_dir / "mix.wav"
    if music:
        fc = (f"[1:a]atrim=0:{total:.3f},volume=-17dB,afade=t=in:d=0.4,"
              f"afade=t=out:st={max(0, total - 1.2):.3f}:d=1.2[m];"
              "[0:a]asplit=2[v1][v2];[m][v1]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[md];"
              "[v2][md][2:a]amix=inputs=3:normalize=0:duration=first,"
              "loudnorm=I=-14:TP=-1.5:LRA=11[out]")
        run(["ffmpeg", "-y", "-i", vo_p, "-stream_loop", "-1", "-i", music, "-i", fx_p, "-filter_complex", fc,
             "-map", "[out]", "-ar", "48000", "-ac", "2", "-t", f"{total:.3f}", mix])
    else:
        run(["ffmpeg", "-y", "-i", vo_p, "-i", fx_p, "-filter_complex",
             "[0:a][1:a]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[out]",
             "-map", "[out]", "-ar", "48000", "-ac", "2", "-t", f"{total:.3f}", mix])
    return mix


def pick_music(pj: dict) -> Path | None:
    want = (pj.get("music") or "").strip()
    if want.lower() in ("none", "off", "no"):
        return None
    if want:
        p = Path(want) if Path(want).is_absolute() else config.MUSIC / want
        return p if p.exists() else None
    tracks = sorted(p for p in config.MUSIC.glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg", ".aac"))
    if not tracks:
        return None
    return tracks[sum(map(ord, pj["_slug"])) % len(tracks)]


# ---------------- one variant ----------------
def build_variant(pj: dict, fmt: str, hook: dict, body: list[dict], cta: dict, res: dict,
                  out: Path, renderer) -> Path:
    cache = res["seg_cache"]
    work = res["build_dir"] / f"{fmt}_{hook['id']}"
    work.mkdir(parents=True, exist_ok=True)
    lines = [dict(hook, _role="hook")] + [dict(b, _role="body") for b in body] + [dict(cta, id="cta", _role="cta")]
    timeline, t, talk_n, broll_n = [], 0.0, 0, 0
    for i, ln in enumerate(lines):
        audio = res["audio"][ln["id"]]
        dur = frames(duration(audio) + GAP) / FPS
        vis = (ln.get("visual") or "talk").strip()
        seg = {"id": ln["id"], "role": ln["_role"], "start": t, "dur": dur, "audio": audio, "text": ln.get("say", ""),
               "chip": (ln.get("text") or "").strip() if ln["_role"] == "body" else ""}
        if ln["_role"] == "cta":
            seg["dur"] = frames(dur + 0.9) / FPS          # hold the end card a moment after the voice ends
            seg["file"] = seg_broll("end", res["endcard"], seg["dur"], cache, res, 0)
            seg["no_caption"] = True
        elif fmt == "selfie" and vis == "talk" and res["clips"].get(("selfie", ln["id"])):
            # alternate a normal and a punched-in framing so jump cuts look intentional
            seg["file"] = seg_talk(res["clips"][("selfie", ln["id"])], dur, cache, zoom=1.0 if talk_n % 2 == 0 else 1.09)
            talk_n += 1
        elif fmt == "greenscreen" and res["clips"].get(("greenscreen", ln["id"])):
            kind, src = _resolve_visual(vis, pj, res, broll_n, filler=vis == "talk")
            bg = seg_broll(kind, src, dur, cache, res, seed=broll_n, layout="gs")
            broll_n += 1
            seg["file"] = seg_greenscreen(bg, res["clips"][("greenscreen", ln["id"])],
                                          res["masks"][("greenscreen", ln["id"])], dur, cache)
        else:
            kind, src = _resolve_visual(vis, pj, res, broll_n, filler=vis == "talk")
            seg["file"] = seg_broll(kind, src, dur, cache, res, seed=broll_n)
            seg["whoosh"] = i > 0
            broll_n += 1
        timeline.append(seg)
        t += seg["dur"]
    total = t

    # ---- overlays (titles, chips) as transparent PNGs
    colors = res["colors"]
    overlays = []
    title = (hook.get("text") or "").strip()
    if title:
        png = work / "title.png"
        renderer.template("overlays/hook.html", png, W, H, transparent=True, text=title, c=colors,
                          style=pj.get("title_style", "white"), top=200 if fmt != "greenscreen" else 105)
        title_end = timeline[0]["dur"] if fmt != "greenscreen" else timeline[-1]["start"]
        overlays.append((png, 0.0, title_end))
    for seg in timeline:
        if seg.get("chip") and fmt != "greenscreen":   # green-screen keeps its title on screen instead
            png = work / f"chip_{seg['id']}.png"
            renderer.template("overlays/chip.html", png, W, H, transparent=True, text=seg["chip"], c=colors,
                              top=430 if fmt == "greenscreen" else 300)
            overlays.append((png, seg["start"] + 0.15, seg["start"] + seg["dur"]))

    # ---- captions
    units = [(s["text"], s["start"] + 0.06, s["start"] + s["dur"] - GAP - 0.08) for s in timeline if not s.get("no_caption")]
    captions.build(units, work / "captions.ass", y=CAPTION_Y[fmt], style=pj.get("caption_style", "pop"),
                         highlight=pj.get("caption_highlight"))

    # ---- audio
    mix = build_audio(timeline, total, work, res.get("music"), sfx=pj.get("sfx", True))

    # ---- final encode
    lst = work / "segments.txt"
    lst.write_text("".join(f"file '{Path(s['file']).as_posix()}'\n" for s in timeline), encoding="utf-8")
    inputs = ["-f", "concat", "-safe", "0", "-i", lst, "-i", mix]
    fc, last = [], "[0:v]"
    for k, (png, a, b) in enumerate(overlays):
        inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", png]
        fc.append(f"{last}[{k + 2}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[o{k}]")
        last = f"[o{k}]"
    fonts_rel = os.path.relpath(config.FONTS, work).replace("\\", "/")
    fc.append(f"{last}ass=captions.ass:fontsdir={fonts_rel},format=yuv420p[v]")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "faster", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", out]
    run(cmd, cwd=work)
    return out
