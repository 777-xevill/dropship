"""Bangla voice-over.

Primary: Gemini TTS (free tier, natural Bangla, a designed voice per character = same voice in every ad).
Fallback: edge-tts Microsoft neural voices (free, no key, flatter). Only used if the character allows it,
because switching engines changes the voice.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

from . import config
from .bangla import speakable
from .util import StudioError, run, say, sha

GAP_START, GAP_END = 0.06, 0.12
_EXHAUSTED: set = set()      # models whose free daily quota ran out during this run
FALLBACK_USED: list = []     # lines spoken by a fallback model instead of the character's designed voice


def _gemini_tts(text: str, out_raw: Path, voice: dict, style: str) -> None:
    from .llm import client
    vid = voice.get("id")
    name = voice.get("name") or "Sulafat"
    last = None
    for model in config.TTS_MODELS:
        if model in _EXHAUSTED:
            continue
        new_api = model.startswith("gemini-3.8")  # 3.8: designed voices, speech_metadata.style, <pause> tags
        if new_api:
            part = {"text": text, **({"speech_metadata": {"style": style}} if style else {})}
        else:  # older TTS models: style as an instruction, paragraph breaks instead of tags
            plain = re.sub(r"\s*<(?:long|short) pause>\s*", "\n\n...\n\n", text)
            part = {"text": (f"Read the following Bangla aloud, {style}:\n\n" if style else "") + plain}
        voice_cfg = {"voice": vid} if (vid and new_api) else {"prebuilt_voice_config": {"voice_name": name}}
        for attempt in range(6):
            try:
                r = client().models.generate_content(
                    model=model, contents=[{"role": "user", "parts": [part]}],
                    config={"response_modalities": ["AUDIO"], "speech_config": {"voice_config": voice_cfg}})
                data = r.candidates[0].content.parts[0].inline_data.data
                if data[:4] != b"RIFF":  # raw PCM 24 kHz mono 16-bit -> wrap in WAV
                    import wave
                    with wave.open(str(out_raw), "wb") as w:
                        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(data)
                else:
                    out_raw.write_bytes(data)
                if vid and not new_api:
                    FALLBACK_USED.append(model)
                return
            except Exception as e:  # noqa: BLE001
                last = e
                msg = str(e)
                if "404" in msg or "not found" in msg.lower() or ("INVALID_ARGUMENT" in msg and "voice" in msg.lower()):
                    break
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "503" in msg or "UNAVAILABLE" in msg or "500" in msg:
                    m = re.search(r"retry(?:Delay)?['\"]?:?\s*['\"]?(\d+)", msg, re.I) or re.search(r"in (\d+(?:\.\d+)?)s", msg)
                    wait = min(90, float(m.group(1)) + 2) if m else 15 * (attempt + 1)
                    if "per day" in msg.lower() or "PerDay" in msg:
                        _EXHAUSTED.add(model)
                        nxt = [m for m in config.TTS_MODELS if m not in _EXHAUSTED]
                        say(f"voice: free daily limit reached on {model}"
                            + (f", using {nxt[0]} (may sound slightly different)" if nxt else ""), kind="warn")
                        break  # daily cap on this model: try the next model
                    say(f"voice: rate limited on {model}, waiting {wait:.0f}s", kind="warn")
                    time.sleep(wait)
                    continue
                if "candidates" in msg or "NoneType" in msg or "index" in msg:
                    time.sleep(3)
                    continue
                raise StudioError(f"Gemini TTS error: {msg[:400]}") from e
    raise StudioError(f"Gemini TTS failed on all models: {str(last)[:300]}")


def _edge_tts(text: str, out_raw: Path, voice: dict) -> None:
    v = voice.get("edge_voice") or "bn-BD-NabanitaNeural"
    p = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", v, "--rate", voice.get("edge_rate", "+0%"),
                        "--text", text, "--write-media", str(out_raw)], capture_output=True, text=True)
    if p.returncode != 0 or not out_raw.exists():
        raise StudioError(f"edge-tts failed: {p.stderr[-300:]}")


def _polish(src: Path, dst: Path, tempo: float = 1.0) -> None:
    """Trim silence, add tiny pads, level to a consistent loudness, 48 kHz mono."""
    trim = ("silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,areverse,"
            "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.05,areverse")
    tmp = dst.with_suffix(".tmp.wav")
    af = trim + (f",atempo={tempo:.4f}" if abs(tempo - 1) > 1e-3 else "")
    run(["ffmpeg", "-y", "-i", src, "-af", af, "-ar", "48000", "-ac", "1", tmp])
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    mean = re.search(r"mean_volume:\s*(-?[\d.]+)", p.stderr)
    peak = re.search(r"max_volume:\s*(-?[\d.]+)", p.stderr)
    gain = 0.0
    if mean and peak:
        gain = min(-19.0 - float(mean.group(1)), -1.0 - float(peak.group(1)))
    run(["ffmpeg", "-y", "-i", tmp, "-af",
         f"volume={gain:.2f}dB,adelay={int(GAP_START * 1000)},apad=pad_dur={GAP_END}",
         "-ar", "48000", "-ac", "1", dst])
    tmp.unlink(missing_ok=True)


def synth(text: str, out_dir: Path, key: str, ch: dict, *, mood: str = "", tempo: float = 1.0) -> Path:
    """Speak one line in the character's voice. Cached: same text+voice -> same file."""
    voice = dict(ch.get("voice") or {})
    spoken = speakable(text)
    style = ", ".join(s for s in (voice.get("style", ""), mood) if s)
    engine = voice.get("engine", "gemini")
    tag = _tag(spoken, voice, style, engine, tempo)
    out = out_dir / f"{key}_{tag}.wav"
    if out.exists():
        return out
    raw = out_dir / f"{key}_{tag}.raw.wav"
    if engine == "gemini" and config.GEMINI_API_KEY:
        try:
            _gemini_tts(spoken, raw, voice, style)
        except StudioError:
            if not voice.get("allow_edge_fallback"):
                raise
            say("Gemini TTS unavailable, using edge-tts fallback (different voice!)", kind="warn")
            raw = raw.with_suffix(".mp3")
            _edge_tts(spoken, raw, voice)
    else:
        raw = raw.with_suffix(".mp3")
        _edge_tts(spoken, raw, voice)
    _polish(raw, out, tempo)
    raw.unlink(missing_ok=True)
    return out


def speed_up(wav: Path, speed: float) -> Path:
    """Faster delivery without changing pitch (cached next to the original)."""
    if abs(speed - 1) < 0.01:
        return wav
    out = wav.with_name(f"{wav.stem}_s{speed:.2f}.wav")
    if not out.exists():
        run(["ffmpeg", "-y", "-i", wav, "-af", f"atempo={speed:.3f}", "-ar", "48000", "-ac", "1", out])
    return out


def _tag(spoken: str, voice: dict, style: str, engine: str, tempo: float = 1.0) -> str:
    return sha(spoken, voice.get("id"), voice.get("name"), voice.get("edge_voice"), style, engine, round(tempo, 3))


def _split_on_pauses(wav: Path, n: int, weights: list[float]) -> list[tuple[float, float]] | None:
    """Find the n-1 longest silences in a batch recording and cut there. None if the result looks wrong."""
    import numpy as np
    from scipy.io import wavfile
    sr, a = wavfile.read(wav)
    a = a.astype(np.float32)
    if a.ndim > 1:
        a = a.mean(axis=1)
    hop = int(sr * 0.01)
    frames = len(a) // hop
    if frames < 10:
        return None
    rms = np.sqrt(np.mean(a[: frames * hop].reshape(frames, hop) ** 2, axis=1) + 1e-9)
    db = 20 * np.log10(rms / (rms.max() + 1e-9))
    silent = db < -38
    runs, i = [], 0
    while i < frames:
        if silent[i]:
            j = i
            while j < frames and silent[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    voiced = np.where(~silent)[0]
    if not len(voiced):
        return None
    first, last = voiced[0], voiced[-1] + 1
    inner = [(s, e) for s, e in runs if s > first and e < last and e - s >= 18]   # >= 180 ms
    if len(inner) < n - 1:
        return None
    cuts = sorted(sorted(inner, key=lambda r: r[1] - r[0], reverse=True)[: n - 1])
    bounds, start = [], first
    for s, e in cuts:
        bounds.append((start * 0.01, s * 0.01 + 0.02))
        start = e - 2
    bounds.append((start * 0.01, last * 0.01))
    durs = [e - s for s, e in bounds]
    ratios = [d / w for d, w in zip(durs, weights)]
    med = sorted(ratios)[len(ratios) // 2]
    if any(r < med * 0.45 or r > med * 2.2 for r in ratios):
        return None   # a line was probably merged or split: fall back to one request per line
    return bounds


def synth_many(items: list[tuple[str, str]], out_dir: Path, ch: dict, *, mood: str = "") -> dict[str, Path]:
    """Speak many lines in ONE request (free tier = 10 requests/day/model), then cut at the pauses.
    Same voice, same mood, consistent loudness. Falls back to one request per line if the cut looks wrong."""
    from .bangla import word_weight
    voice = dict(ch.get("voice") or {})
    style = ", ".join(s for s in (voice.get("style", ""), mood) if s)
    engine = voice.get("engine", "gemini")
    result, todo = {}, []
    for key, text in items:
        spoken = speakable(text)
        out = out_dir / f"{key}_{_tag(spoken, voice, style, engine)}.wav"
        if out.exists():
            result[key] = out
        else:
            todo.append((key, text, spoken, out))
    if len(todo) >= 2 and engine == "gemini" and config.GEMINI_API_KEY:
        raw = out_dir / f"batch_{sha([t[2] for t in todo], style)}.raw.wav"
        joined = "\n\n<long pause>\n\n".join(t[2] for t in todo)
        try:
            if not raw.exists():
                _gemini_tts(joined, raw, voice, style + (", leave a clear pause between sentences" if style else "leave a clear pause between sentences"))
            weights = [sum(word_weight(w) for w in t[2].split()) for t in todo]
            bounds = _split_on_pauses(raw, len(todo), weights)
        except StudioError as e:
            say(f"batch voice failed ({str(e)[:120]}), trying line by line", kind="warn")
            bounds = None
        if bounds:
            for (key, _text, _spoken, out), (s, e) in zip(todo, bounds):
                piece = out.with_suffix(".cut.wav")
                run(["ffmpeg", "-y", "-i", raw, "-ss", f"{max(0, s - 0.03):.3f}", "-to", f"{e + 0.05:.3f}", piece])
                _polish(piece, out)
                piece.unlink(missing_ok=True)
                result[key] = out
            raw.unlink(missing_ok=True)
            return result
        say("could not cut the batch cleanly, using one request per line", kind="warn")
    for key, text, _spoken, _out in todo:
        result[key] = synth(text, out_dir, key, ch, mood=mood)
    return result


def design_voice(description: str, display_name: str, language: str = "bn-BD", gender: str = "female") -> dict:
    """Create a persistent custom Gemini voice (lives 1 year after last use). Returns {'id', 'sample'}."""
    import base64
    from .llm import client
    v = client().voices.create(voice={"type": "prompted", "prompted": {"input": description},
                                      "display_name": display_name[:60], "language_code": language,
                                      "gender": gender}, store=True)
    d = v.model_dump(exclude_none=True) if hasattr(v, "model_dump") else dict(v)
    sample = None
    sa = d.get("sample_audio") or {}
    if sa.get("data"):
        raw = sa["data"]
        sample = base64.b64decode(raw) if isinstance(raw, str) else raw
    return {"id": d.get("id"), "sample": sample}
