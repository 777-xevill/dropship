"""Scene stills via the Gemini image models (free API key). Same prompts as gen_scenes.py.
Usage: gen_gemini.py [--model M] [scene names...]"""
import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.path.insert(0, r"E:\Dropship\studio")
sys.path.insert(0, str(Path(__file__).parent))
from studio.llm import client  # noqa: E402
from gen_scenes import SCENES, SAIMA, BOTTLE, S, B, LOOK, KEEP, KEEP_P, OUT  # noqa: E402

args = sys.argv[1:]
models = ["gemini-3.1-flash-image", "gemini-3.1-flash-image-preview", "gemini-2.5-flash-image", "gemini-3-pro-image"]
if args and args[0] == "--model":
    models, args = [args[1]], args[2:]
only = set(args)

for name, (refs, text) in SCENES.items():
    if only and name not in only:
        continue
    out = OUT / f"{name}.png"
    if out.exists():
        print("exists", name)
        continue
    parts = []
    for r in refs:
        p = SAIMA if r == S else BOTTLE
        parts.append({"inline_data": {"mime_type": "image/png", "data": p.read_bytes()}})
    prompt = text + (LOOK if S in refs else "") + (KEEP if S in refs else "Photorealistic, no text, no logo, no watermark. ") + (KEEP_P if B in refs else "")
    prompt += " Output one tall vertical 9:16 portrait image."
    parts.append({"text": prompt})
    done = False
    for m in models:
        try:
            r = client().models.generate_content(
                model=m, contents=[{"role": "user", "parts": parts}],
                config={"response_modalities": ["IMAGE"], "image_config": {"aspect_ratio": "9:16"}})
            for c in r.candidates or []:
                for pt in (c.content.parts if c.content else []) or []:
                    if getattr(pt, "inline_data", None) and pt.inline_data.data:
                        Image.open(BytesIO(pt.inline_data.data)).convert("RGB").save(out)
                        done = True
                        break
            if done:
                im = Image.open(out)
                print("made", name, m, im.size, flush=True)
                break
            print("no image", name, m, (r.text or "")[:150], flush=True)
        except Exception as e:  # noqa: BLE001
            print("FAIL", name, m, str(e)[:220], flush=True)
    time.sleep(4)
