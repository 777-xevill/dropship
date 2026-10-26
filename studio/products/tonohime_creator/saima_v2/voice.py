"""Record both scripts in Saima's designed Gemini voice (one request per video), then clean the audio:
high-pass (removes the 60-70 Hz rumble heard as 'hum'), FFT denoise, gentle compression, fixed level."""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\Dropship\studio")
sys.path.insert(0, str(Path(__file__).parent))
from studio import voice  # noqa: E402
from studio.project import load_character  # noqa: E402
from studio.util import duration, run  # noqa: E402
from script import V1, V2  # noqa: E402

HERE = Path(__file__).parent
RAW = HERE / "audio_raw"
CLEAN = HERE / "audio"
RAW.mkdir(exist_ok=True)
CLEAN.mkdir(exist_ok=True)
ch = load_character("creator")

CHAIN = ("highpass=f=90:poles=2,lowpass=f=13000,afftdn=nr=12:nf=-50:tn=1,"
         "equalizer=f=3200:t=q:w=1.2:g=2,"
         "acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=3dB,"
         "alimiter=limit=0.89:level=false")

for v in (V1, V2):
    got = voice.synth_many(v["lines"], RAW, ch, mood=v["mood"])
    for key, _ in v["lines"]:
        dst = CLEAN / f"{key}.wav"
        run(["ffmpeg", "-y", "-i", got[key], "-af", CHAIN, "-ar", "48000", "-ac", "1", dst])
        print(key, f"{duration(dst):.2f}s")
