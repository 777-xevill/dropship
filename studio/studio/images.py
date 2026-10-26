"""Scene images: your character + your product, made with free image-edit models.

Engines (tried in order, configurable with --engine):
  qwen   Qwen-Image-Edit-2511 + Lightning (Apache-2.0) on a free HF Space. Strong identity + product fidelity.
  flux   FLUX.2-klein-4B (Apache-2.0) on a free HF Space. Very cheap on quota; tested 2026-10-15: same face,
         outfit and product kept across 3 scenes with no account at all.
  manual You make the image in any free web app (Gemini app, Qwen Chat, Copilot...) and drop it in inbox/.
Identity comes from the reference PHOTOS, not from words: image 1 = character, image 2 = product.
"""
import shutil
from pathlib import Path

from PIL import Image

from . import config, hf
from .project import inbox_file, todo_done
from .util import StudioError, say

LOCK = (" Keep the person's face, skin tone, hair and body exactly the same as in image 1 (same identity). "
        "Keep the product exactly as in image 2: same shape, colours, cap and label design. "
        "Photorealistic, natural skin texture, real smartphone photo quality. No text, no captions, no watermark.")

SIZES = {  # (width, height) requested from the models
    "9:16": {"qwen": (768, 1344), "flux": (576, 1024)},
    "4:5": {"qwen": (1024, 1280), "flux": (816, 1024)},
    "1:1": {"qwen": (1024, 1024), "flux": (1024, 1024)},
}


def _gallery(paths):
    from gradio_client import handle_file
    return [{"image": handle_file(str(p)), "caption": None} for p in paths]


def _qwen(refs, prompt, out, aspect):
    w, h = SIZES[aspect]["qwen"]
    fast = "fast" in config.SPACE_EDIT_BEST.lower() or "lightning" in config.SPACE_EDIT_BEST.lower()
    steps, cfg = (4, 1.0) if fast else (28, 4.0)
    r = hf.call(config.SPACE_EDIT_BEST,
                lambda c: c.predict(_gallery(refs), prompt, 0, True, cfg, steps, h, w, False, api_name="/infer"))
    return hf.save_output(r, out)


def _flux(refs, prompt, out, aspect):
    w, h = SIZES[aspect]["flux"]
    r = hf.call(config.SPACE_EDIT_FAST,
                lambda c: c.predict(prompt, _gallery(refs), "Distilled (4 steps)", 0, True, w, h, 4, 1.0, False,
                                    api_name="/infer"))
    return hf.save_output(r, out)


ENGINES = {"qwen": _qwen, "flux": _flux}


def make_image(name: str, prompt: str, refs: list[Path], out: Path, pj: dict,
               aspect: str = "9:16", engines=("qwen", "flux", "manual")) -> Path | None:
    """Create one scene image. Returns the path, or None if it is waiting for a manual file."""
    dropped = inbox_file(pj, f"scene_{name}", {".png", ".jpg", ".jpeg", ".webp", ".jfif"})
    if dropped:
        Image.open(dropped).convert("RGB").save(out)
        dropped.rename(dropped.with_name(dropped.stem + "_used" + dropped.suffix))
        todo_done(pj, f"scene_{name}")
        say(f"scene '{name}': imported {dropped.name} from inbox", kind="ok")
        return out
    if out.exists():
        todo_done(pj, f"scene_{name}")
        return out
    full = prompt.strip().rstrip(".") + "." + LOCK
    errors = []
    for eng in engines:
        if eng == "manual":
            _manual_todo(pj, name, full, refs, aspect)
            say(f"scene '{name}': waiting for you -> see inbox/TODO.md", kind="warn")
            return None
        try:
            say(f"scene '{name}': generating with {eng} (free HF Space)...", kind="info")
            ENGINES[eng](refs, full, out, aspect)
            todo_done(pj, f"scene_{name}")
            say(f"scene '{name}' -> {out.name}", kind="ok")
            return out
        except hf.QuotaError as e:
            errors.append(f"{eng}: {e}")
            say(f"{eng}: {e}", kind="warn")
        except StudioError as e:
            errors.append(f"{eng}: {e}")
            say(f"{eng} failed: {str(e)[:200]}", kind="warn")
    if not errors:
        return None  # no engine asked for: only existing / inbox files are used
    raise StudioError("All image engines failed:\n  " + "\n  ".join(errors))


def _manual_todo(pj, name, prompt, refs, aspect):
    inbox = pj["_dir"] / "inbox"
    ref_dir = inbox / "upload_these"
    ref_dir.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(refs, 1):
        dst = ref_dir / f"{name}_ref{i}{Path(r).suffix}"
        if not dst.exists():
            shutil.copy2(r, dst)
    todo = inbox / "TODO.md"
    block = (f"\n## scene_{name}  ({aspect})\n"
             f"1. Open a free image tool (Gemini app: gemini.google.com | Qwen Chat: chat.qwen.ai | Copilot).\n"
             f"2. Upload: {', '.join(f'upload_these/{name}_ref{i}{Path(r).suffix}' for i, r in enumerate(refs, 1))}\n"
             f"3. Paste this prompt (ask for {aspect} vertical):\n\n```\n{prompt}\n```\n"
             f"4. Save the result into inbox/ as  scene_{name}.png  and run the command again.\n")
    text = todo.read_text(encoding="utf-8") if todo.exists() else "# Things to make by hand (free web tools)\n"
    if f"## scene_{name} " not in text:
        todo.write_text(text + block, encoding="utf-8")
