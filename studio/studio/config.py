"""Paths, keys and environment for the studio.

Everything heavy (model caches, temp files, Gradio downloads) is kept on E:
because C: is almost full on this machine.
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # E:\Dropship\studio
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
MUSIC = ASSETS / "music"
TEMPLATES = ROOT / "templates"
CHARACTERS = ROOT / "characters"
PRODUCTS = ROOT / "products"
CACHE = ROOT / ".cache"
MODELS = CACHE / "models"

# Keep every library cache off C:
os.environ.setdefault("HF_HOME", str(CACHE / "hf"))
os.environ.setdefault("GRADIO_TEMP_DIR", str(CACHE / "gradio"))
os.environ.setdefault("U2NET_HOME", str(CACHE / "u2net"))
os.environ.setdefault("PIP_CACHE_DIR", str(CACHE / "pip"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _d in (CACHE, MODELS, CACHE / "hf", CACHE / "gradio", CACHE / "u2net", CACHE / "tmp"):
    _d.mkdir(parents=True, exist_ok=True)

# rembg model already downloaded on C: by an earlier project: reuse it instead of re-downloading
_old_u2net = Path.home() / ".u2net" / "isnet-general-use.onnx"
_new_u2net = CACHE / "u2net" / "isnet-general-use.onnx"
if _old_u2net.exists() and not _new_u2net.exists():
    try:
        shutil.copy2(_old_u2net, _new_u2net)
    except OSError:
        pass

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip() or None

# Free-tier Gemini models (checked 2026-10-15 on ai.google.dev/gemini-api/docs/pricing).
# The first one that works is used; later ones are fallbacks if Google renames/retires a model.
TEXT_MODELS = [m.strip() for m in os.environ.get(
    "STUDIO_TEXT_MODELS", "gemini-3.8-flash,gemini-3.6-flash,gemini-2.5-flash").split(",") if m.strip()]
# Free tier = 10 requests/day per model (checked 2026-10-15), so lines are batched: ~2 requests per product.
# Designed (custom) voices only work on the 3.8 models; the others fall back to the prebuilt voice name.
TTS_MODELS = [m.strip() for m in os.environ.get(
    "STUDIO_TTS_MODELS",
    "gemini-3.8-flash-tts,gemini-3.8-flash-lite-tts,gemini-3.1-flash-tts-preview,gemini-2.5-flash-preview-tts").split(",") if m.strip()]

# Free Hugging Face Spaces used as GPU engines (ZeroGPU quota: 2 min/day anonymous, 5 min/day with a free token)
SPACE_TALK = os.environ.get("STUDIO_SPACE_TALK", "alexnasa/ltx-2-TURBO")
SPACE_TALK_ALT = os.environ.get("STUDIO_SPACE_TALK_ALT", "multimodalart/ltx2-audio-to-video")
# Qwen-Image-Edit-2511 + Lightning LoRA (4 steps, 60 s GPU request). The official Qwen Space asks for 360 s
# per call, more than a free account may request, so it only works for HF PRO users.
SPACE_EDIT_BEST = os.environ.get("STUDIO_SPACE_EDIT_BEST", "linoyts/Qwen-Image-Edit-2511-Fast")
SPACE_EDIT_FAST = os.environ.get("STUDIO_SPACE_EDIT_FAST", "black-forest-labs/FLUX.2-klein-4B")

# Output video
W, H, FPS = 1080, 1920, 30

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def tmpdir(name: str) -> Path:
    d = CACHE / "tmp" / name
    d.mkdir(parents=True, exist_ok=True)
    return d
