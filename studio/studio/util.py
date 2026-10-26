"""Small shared helpers: logging, ffmpeg/ffprobe, hashing."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def say(msg: str = "", *, kind: str = "") -> None:
    prefix = {"ok": "  [ok] ", "warn": "  [!] ", "err": "  [x] ", "step": "\n== ", "info": "  - "}.get(kind, "")
    text = f"{prefix}{msg}"
    try:
        print(text, flush=True)
    except UnicodeEncodeError:  # old Windows consoles
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        sys.stdout.flush()


class StudioError(Exception):
    """An error with a message the user can act on."""


def run(cmd, *, cwd=None, quiet=True) -> subprocess.CompletedProcess:
    cmd = [str(c) for c in cmd]
    if cmd[0] in ("ffmpeg", "ffprobe") and quiet:
        cmd[1:1] = ["-hide_banner", "-loglevel", "error"]
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise StudioError(f"Command failed: {' '.join(cmd[:6])} ...\n{p.stderr.strip()[-1500:]}")
    return p


def duration(path) -> float:
    p = run(["ffprobe", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(p.stdout.strip())


def video_info(path) -> dict:
    p = run(["ffprobe", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
             "-of", "json", path])
    data = json.loads(p.stdout)
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    num, _, den = (v.get("r_frame_rate") or "30/1").partition("/")
    return {"width": v.get("width"), "height": v.get("height"),
            "fps": float(num) / float(den or 1), "has_audio": a is not None,
            "duration": float(data.get("format", {}).get("duration", 0) or 0)}


def sha(*parts, n: int = 12) -> str:
    h = hashlib.sha1()
    for p in parts:
        if isinstance(p, Path) or (isinstance(p, str) and len(p) < 400 and Path(p).is_file()):
            path = Path(p)
            st = path.stat()
            h.update(f"{path.resolve()}|{st.st_size}|{st.st_mtime_ns}".encode())
        else:
            h.update(json.dumps(p, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:n]


def ffpath(p) -> str:
    """Path for use *inside* an ffmpeg filtergraph (escape the drive colon and backslashes)."""
    s = str(Path(p).resolve()).replace("\\", "/")
    return s.replace(":", r"\:").replace("'", r"\'")
