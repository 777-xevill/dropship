"""Talking clips: your character speaks the Bangla voice-over with real lip-sync and body motion.

Engine 'ltx': LTX-2 (Lightricks, free licence under $10M revenue) on the free HF Space alexnasa/ltx-2-TURBO.
  image + our audio -> 1024x1536 talking video, 3/5/10/15 s, no watermark.
  Cost on the free daily GPU quota (x2 because the Space uses a big GPU): 3 s ~ 70 s, 5 s ~ 100 s.
  -> roughly 10-20 seconds of talking video per day with a free HF token.
Engine 'manual': we export the image + audio; you make the clip in a free web tool and drop it in inbox/.
"""
import json
import shutil
from pathlib import Path

import httpx

from . import config, hf
from .project import inbox_file, todo_done
from .util import StudioError, duration, run, say

BUCKETS = (3, 5, 10, 15)
MAX_SQUEEZE = 1.07          # speed a line up by at most 7% to fit a cheaper bucket
_duration_fn: dict = {}


def plan(seconds: float) -> tuple[int, float]:
    """Pick the clip length to request and the tempo needed for the audio to fit it."""
    if seconds > BUCKETS[-1] * MAX_SQUEEZE:
        raise StudioError(f"A talking line is {seconds:.1f}s long; max is 15s. Split it into shorter sentences.")
    for b in BUCKETS:
        if seconds <= b:
            return b, 1.0
        if seconds <= b * MAX_SQUEEZE:
            return b, seconds / b
    return BUCKETS[-1], seconds / BUCKETS[-1]


def _set_duration(c, seconds: int) -> None:
    """The Space keeps clip length in per-session state that only its dropdown changes.
    Send the same event the dropdown sends, in our own session."""
    key = c.src
    if key not in _duration_fn:
        cfg = c.config
        comps = {x["id"]: x for x in cfg["components"]}
        dur_ui = next((k for k, v in comps.items() if (v.get("props") or {}).get("elem_id") == "duration_ui"), None)
        dep = next(((i, d) for i, d in enumerate(cfg["dependencies"]) if dur_ui in (d.get("inputs") or [])), None)
        if dur_ui is None or dep is None:
            raise StudioError("Could not find the clip-length control on the LTX Space (it may have changed).")
        idx, d = dep
        _duration_fn[key] = (d.get("id", idx), dur_ui)
    fn_index, trigger = _duration_fn[key]
    base = c.src.rstrip("/") + "/" + (c.api_prefix or "gradio_api").strip("/")   # api_prefix looks like 'gradio_api/'
    headers = dict(c.headers or {})
    r = httpx.post(base + "/queue/join", headers=headers, timeout=60,
                   json={"data": [f"{seconds}s"], "event_data": None, "fn_index": fn_index,
                         "trigger_id": trigger, "session_hash": c.session_hash})
    if r.status_code != 200:
        raise StudioError(f"Setting clip length failed: HTTP {r.status_code} {r.text[:200]}")
    event_id = r.json().get("event_id")
    with httpx.stream("GET", base + "/queue/data", params={"session_hash": c.session_hash},
                      headers=headers, timeout=120) as s:
        for line in s.iter_lines():
            if not line.startswith("data:"):
                continue
            m = json.loads(line[5:])
            if m.get("event_id") not in (None, event_id):
                continue
            if m.get("msg") == "process_completed":
                if not m.get("success", True):
                    raise StudioError(f"Setting clip length failed: {str(m.get('output'))[:200]}")
                return
            if m.get("msg") == "close_stream":
                return


def _ltx(image: Path, audio: Path, out: Path, prompt: str, bucket: int, size=(512, 768), seed: int = 0):
    from gradio_client import handle_file

    def job(c):
        if bucket != 3:
            _set_duration(c, bucket)        # same session as the generate call below
        return c.predict(handle_file(str(image)), None, prompt, None, "Image-to-Video", False,
                         seed or 42, not seed, size[1], size[0], "No LoRA", handle_file(str(audio)),
                         api_name="/generate_video")
    r = hf.call(config.SPACE_TALK, job)
    tmp = out.with_suffix(".dl.mp4")
    hf.save_output(r, tmp)
    got = duration(tmp)
    if got < bucket - 0.6:
        tmp.unlink(missing_ok=True)
        _duration_fn.clear()
        raise StudioError(f"LTX returned {got:.1f}s instead of {bucket}s (clip-length control failed).")
    tmp.replace(out)


def _ltx_mm(image: Path, audio: Path, out: Path, prompt: str, seconds: float):
    """Second engine: multimodalart/ltx2-audio-to-video (LTX-2 audio-to-video). Any length up to 12 s."""
    import math
    from gradio_client import handle_file
    dur = min(12.0, max(1.0, math.ceil((seconds + 0.1) * 2) / 2))
    r = hf.call(config.SPACE_TALK_ALT, lambda c: c.predict(
        handle_file(str(image)), handle_file(str(audio)), prompt,
        "low quality, worst quality, deformed, distorted, blurry face, extra fingers, text, watermark",
        dur, -1, api_name="/generate"))
    hf.save_output(r, out)


def talk_prompt(ch: dict, scene_hint: str = "") -> str:
    female = (ch.get("gender") or "female").lower().startswith("f")
    who, pos = ("woman", "her") if female else ("man", "his")
    return (f"The {who} in the image is filming a casual selfie video and talks directly to the phone camera, "
            f"speaking warmly and naturally, lips moving exactly in sync with {pos} speech, natural blinks and small head "
            f"movements, relaxed friendly expression, subtle natural hand gestures{', ' + scene_hint if scene_hint else ''}. "
            "Keep the person's face and the product identical to the image. Handheld smartphone footage, realistic, "
            "natural light, no text on screen.")


def clip_path(key: str, image: Path, audio: Path, out_dir: Path) -> Path:
    return out_dir / f"talk_{key}_{image.stem[:12]}_{audio.stem[-12:]}.mp4"


def make_clip(key: str, image: Path, audio: Path, out_dir: Path, pj: dict, ch: dict,
              engines=("ltx", "manual"), size=(512, 768), hint: str = "") -> Path | None:
    """One talking clip for one line. Cached by (image, audio). None = waiting for a manual file."""
    dropped = inbox_file(pj, f"talk_{key}", {".mp4", ".mov", ".webm", ".mkv"})
    out = clip_path(key, image, audio, out_dir)
    if dropped:
        shutil.copy2(dropped, out)
        dropped.rename(dropped.with_name(dropped.stem + "_used" + dropped.suffix))
        todo_done(pj, f"talk_{key}")
        return out
    if out.exists():
        todo_done(pj, f"talk_{key}")
        return out
    secs = duration(audio)
    bucket, tempo = plan(secs)
    if abs(tempo - 1) > 1e-3:
        raise StudioError(f"internal: audio for {key} must be squeezed before make_clip")
    errors = []
    for eng in engines:
        if eng == "manual":
            _manual_todo(pj, key, image, audio, bucket)
            return None
        try:
            if eng == "ltx":
                say(f"talk '{key}': {secs:.1f}s line -> {bucket}s LTX-2 clip (free HF GPU)...", kind="info")
                _ltx(image, audio, out, talk_prompt(ch, hint), bucket, size)
            elif eng == "ltx-mm":
                if secs > 12:
                    raise StudioError("line longer than 12 s")
                say(f"talk '{key}': {secs:.1f}s line -> LTX-2 audio-to-video (free HF GPU)...", kind="info")
                _ltx_mm(image, audio, out, talk_prompt(ch, hint), secs)
            else:
                raise StudioError(f"unknown talk engine '{eng}' (use ltx, ltx-mm or manual)")
        except hf.QuotaError:
            raise                       # quota is shared by all HF engines: no point trying another
        except StudioError as e:
            errors.append(f"{eng}: {e}")
            say(f"{eng} failed: {str(e)[:160]}", kind="warn")
            continue
        todo_done(pj, f"talk_{key}")
        say(f"talk '{key}' done", kind="ok")
        return out
    if errors:
        raise StudioError("; ".join(errors))
    return None


def squeeze_for_clip(audio: Path) -> tuple[Path, int]:
    """If a line is a little longer than a cheap bucket, speed it up slightly (max 7%). Returns (audio, bucket)."""
    secs = duration(audio)
    bucket, tempo = plan(secs)
    if abs(tempo - 1) <= 1e-3:
        return audio, bucket
    out = audio.with_name(audio.stem + f"_x{tempo:.3f}.wav")
    if not out.exists():
        run(["ffmpeg", "-y", "-i", audio, "-af", f"atempo={tempo:.4f}", "-ar", "48000", "-ac", "1", out])
    return out, bucket


def _manual_todo(pj, key, image, audio, bucket):
    inbox = pj["_dir"] / "inbox"
    up = inbox / "upload_these"
    up.mkdir(parents=True, exist_ok=True)
    img_dst, aud_dst = up / f"talk_{key}.png", up / f"talk_{key}.wav"
    if not img_dst.exists():
        shutil.copy2(image, img_dst)
    if not aud_dst.exists():
        shutil.copy2(audio, aud_dst)
    todo = inbox / "TODO.md"
    text = todo.read_text(encoding="utf-8") if todo.exists() else "# Things to make by hand (free web tools)\n"
    if f"## talk_{key} " not in text:
        text += (f"\n## talk_{key}  (lip-sync video, {bucket}s)\n"
                 f"Upload `upload_these/talk_{key}.png` + `upload_these/talk_{key}.wav` to a talking-avatar tool "
                 f"(Dreamina AI Avatar / Kling Avatar / HeyGen photo avatar: free credits, free tiers usually watermark).\n"
                 f"Save the video into inbox/ as  talk_{key}.mp4  and run the command again.\n")
        todo.write_text(text, encoding="utf-8")
