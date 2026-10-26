"""Check every recorded line: transcribe it back with Gemini (is the right sentence in the right file?)
and measure median pitch (did any line come out in a different voice?)."""
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, r"E:\Dropship\studio")
sys.path.insert(0, str(Path(__file__).parent))
from studio import config  # noqa: E402
from studio.llm import client  # noqa: E402
from script import V1, V2  # noqa: E402

A = Path(__file__).parent / "audio"


def pitch(p):
    sr, a = wavfile.read(p)
    a = a.astype(np.float32) / 32768
    f0 = []
    for i in range(0, len(a) - 2048, 480):
        fr = a[i:i + 2048] * np.hanning(2048)
        if np.sqrt((fr ** 2).mean()) < 0.02:
            continue
        ac = np.correlate(fr, fr, "full")[2047:]
        lo, hi = sr // 400, sr // 120
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.3 * ac[0]:
            f0.append(sr / k)
    return float(np.median(f0)) if f0 else 0.0


import time
only = set(sys.argv[1:])
for v in (V1, V2):
    for key, text in v["lines"]:
        if only and key not in only:
            continue
        time.sleep(8)
        p = A / f"{key}.wav"
        data = p.read_bytes()
        said = ""
        for model in config.TEXT_MODELS:
            try:
                r = client().models.generate_content(model=model, contents=[{"role": "user", "parts": [
                    {"inline_data": {"mime_type": "audio/wav", "data": data}},
                    {"text": "Transcribe this Bangla audio exactly, in Bangla script. Output only the transcript."}]}])
                said = (r.text or "").strip()
                break
            except Exception as e:  # noqa: BLE001
                said = f"[{model} failed: {str(e)[:80]}]"
        print(f"{key}  {pitch(p):5.0f} Hz | want: {text}\n{'':16}| got:  {said}")
