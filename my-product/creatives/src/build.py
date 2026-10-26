import subprocess, sys
from PIL import Image

W, H, FPS, XF = 1080, 1920, 30, 0.4
scenes = [("s1.png", 3.4), ("s2.png", 4.4), ("s3.png", 4.4),
          ("s4.png", 4.4), ("s5.png", 5.4), ("s6.png", 3.4)]
out = sys.argv[1]

def frames(path, dur):
    im = Image.open(path).convert("RGB")
    n = int(dur * FPS)
    for k in range(n):
        z = 1 + 0.07 * k / n            # slow push-in
        cw, ch = W / z, H / z
        x, y = (W - cw) / 2, (H - ch) / 2
        yield im.resize((W, H), Image.BILINEAR, box=(x, y, x + cw, y + ch))

ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

xn = int(XF * FPS)
tail = []
for idx, (p, d) in enumerate(scenes):
    last = idx == len(scenes) - 1
    n = int(d * FPS)
    newtail = []
    for k, f in enumerate(frames(p, d)):
        if k < len(tail):  # crossfade previous scene's tail into this head
            f = Image.blend(tail[k], f, (k + 1) / (xn + 1))
        if not last and k >= n - xn:
            newtail.append(f)
        else:
            ff.stdin.write(f.tobytes())
    tail = newtail
ff.stdin.close()
ff.wait()
