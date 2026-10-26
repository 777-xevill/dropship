import math, subprocess, sys
from PIL import Image, ImageFilter, ImageDraw

W, H, FPS, PAD = 720, 1280, 30, 0.35
AD = "../ad/"
out = sys.argv[1]

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", p]).strip())

def fill(im):  # cover-crop to 1080x1920
    r = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS) if r != 1 else im
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))

def card(photo_path, bg):  # product photo as a rounded card on a blurred copy of her scene
    base = bg.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * .55))
    p = Image.open(photo_path).convert("RGB")
    pw = 600; ph = round(p.height * pw / p.width)
    p = p.resize((pw, ph), Image.LANCZOS)
    m = Image.new("L", (pw, ph), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, pw, ph), 40, fill=255)
    base.paste(p, ((W - pw) // 2, 220), m)
    return base

caps = {1: ["cap1_1", "cap1_2", "cap1_3"], 2: ["cap2_1", "cap2_2", "cap2_3"],
        3: ["cap3_1", "cap3_2"], 4: ["cap4_1", "cap4_2", "cap4_3"]}
caplen = {1: [36, 41, 34], 2: [28, 33, 19], 3: [36, 40], 4: [18, 23, 33]}

scenes = []
for s in range(1, 5):
    g = fill(Image.open(f"g{s}.png").convert("RGB"))
    cuts = []
    if s == 2:
        cuts = [(0.2, 2.4, card(AD + "bottles.png", g), True), (2.4, 4.6, card(AD + "texture.png", g), True)]
    if s == 4:
        cuts = [(0.1, 3.8, fill(Image.open(AD + "s5.png").convert("RGB")), False)]
    scenes.append((g, dur(f"vo{s}.mp3"), cuts, [Image.open(c + ".png").convert("RGBA").resize((W, H), Image.LANCZOS) for c in caps[s]], caplen[s]))

ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
    "-r", str(FPS), "-i", "-", "-i", "vo_all.m4a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out],
    stdin=subprocess.PIPE)

for g, d, cuts, caps_im, lens in scenes:
    total = d + PAD
    n = round(total * FPS)
    bounds, acc = [], 0
    for L in lens:
        acc += L / sum(lens) * d; bounds.append(acc)
    for k in range(n):
        t = k / FPS
        frame, cap = None, True
        for a, b, im, c in cuts:
            if a <= t < b:
                frame, cap = im, c
        if frame is None:  # her shot: slow push-in + light handheld drift
            z = 1.02 + 0.05 * t / total
            cw, ch = W / z, H / z
            x = (W - cw) / 2 + 4 * math.sin(t * 1.7)
            y = (H - ch) / 2 + 3 * math.sin(t * 1.3 + 1)
            frame = g.resize((W, H), Image.BILINEAR, box=(x, y, x + cw, y + ch))
        ci = next((i for i, b in enumerate(bounds) if t < b), len(caps_im) - 1)
        if cap:
            frame = Image.alpha_composite(frame.convert("RGBA"), caps_im[ci]).convert("RGB")
        ff.stdin.write(frame.tobytes())
ff.stdin.close(); ff.wait()
