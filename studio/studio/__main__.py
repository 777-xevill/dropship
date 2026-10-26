"""studio - free Bangla UGC video + poster factory.   Run  `studio help`  for the walkthrough."""
import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

from . import config
from .util import StudioError, say

HELP = """
STUDIO  -  free Bangla UGC videos + posters with ONE consistent character

  First time only
    studio doctor                                   check everything is installed and keys work
    studio character maya --image "D:\\pics\\maya.png"   lock your character (+ her Bangla voice)

  Every product
    studio product tonohime --photos p1.jpg p2.jpg --name "TONO HIME Gel" --character maya
    studio write tonohime                           Gemini writes the Bangla script + 10 hooks (edit project.yaml after)
    studio make tonohime                            voice -> images -> talking clips -> videos -> posters
    studio make tonohime                            ...run again tomorrow: continues where the free GPU quota stopped
    studio status tonohime                          what is done / waiting
    studio log tonohime                             add the finished files to 03-logs/creative-log.md

  Single steps (make runs all of them)
    studio voice | scenes | talk | build | posters <slug>
    options:  --formats selfie,greenscreen,faceless   --hooks h01,h03   --engine qwen,flux,manual / ltx,ltx-mm,manual
"""


def _csv(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else None


# ---------------------------------------------------------------- doctor
def cmd_doctor(a):
    ok = True
    say("Checking studio", kind="step")
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            say(f"{tool} found", kind="ok")
        else:
            ok = False
            say(f"{tool} missing  ->  winget install Gyan.FFmpeg", kind="err")
    edge = next((p for p in config.EDGE_PATHS if Path(p).exists()), None)
    say(f"browser for rendering: {edge}" if edge else "Edge/Chrome not found (posters + titles need it)", kind="ok" if edge else "err")
    ok &= bool(edge)
    fonts = list(config.FONTS.glob("*.ttf"))
    say(f"{len(fonts)} fonts in assets/fonts", kind="ok" if len(fonts) >= 10 else "err")
    for mod, pkg in (("gradio_client", "gradio_client"), ("google.genai", "google-genai"), ("playwright", "playwright"),
                     ("rembg", "rembg"), ("onnxruntime", "onnxruntime"), ("edge_tts", "edge-tts"), ("jinja2", "jinja2"),
                     ("scipy", "scipy"), ("yaml", "pyyaml")):
        try:
            __import__(mod)
            say(f"python: {pkg}", kind="ok")
        except ImportError:
            ok = False
            say(f"python package missing: {pkg}  ->  studio setup", kind="err")
    say("GEMINI_API_KEY set" if config.GEMINI_API_KEY else "GEMINI_API_KEY missing in studio/.env (free: aistudio.google.com/apikey)",
        kind="ok" if config.GEMINI_API_KEY else "err")
    say("HF_TOKEN set (5 free GPU-min/day)" if config.HF_TOKEN else
        "HF_TOKEN not set: works, but only 2 free GPU-min/day. Free token: huggingface.co/settings/tokens", kind="ok" if config.HF_TOKEN else "warn")
    if config.GEMINI_API_KEY and a.test:
        try:
            from .voice import synth
            d = config.tmpdir("doctor")
            for old in d.glob("*.wav"):
                old.unlink()
            # test on the last (backup) model so the 10/day quota of the main voice model stays untouched
            config.TTS_MODELS[:] = config.TTS_MODELS[-1:] + config.TTS_MODELS[:-1]
            p = synth("পরীক্ষা চলছে, সব ঠিক আছে।", d, "test", {"voice": {"name": "Sulafat"}})
            say(f"Gemini TTS works ({p.name})", kind="ok")
        except StudioError as e:
            ok = False
            say(f"Gemini TTS test failed: {e}", kind="err")
    free_c = shutil.disk_usage("C:\\").free / 1e9
    say(f"C: free {free_c:.1f} GB (studio keeps its caches on E:)", kind="ok" if free_c > 0.5 else "warn")
    say("All good." if ok else "Fix the [x] items above.", kind="step")


def cmd_setup(a):
    import subprocess
    req = config.ROOT / "requirements.txt"
    say("Installing python packages into studio/.venv ...", kind="step")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req)], check=False)
    cmd_doctor(argparse.Namespace(test=False))


# ---------------------------------------------------------------- character
def cmd_character(a):
    from . import llm, voice
    from .project import IMG_EXT, character_dir, write_yaml
    d = character_dir(a.name)
    (d / "ref").mkdir(parents=True, exist_ok=True)
    imgs = [Path(p) for p in (a.image or [])]
    for p in imgs:
        if not p.exists() or p.suffix.lower() not in IMG_EXT:
            raise StudioError(f"Not an image: {p}")
    if imgs:  # new photos replace the old set, so an old 'main' can never win
        for old in (d / "ref").glob("*"):
            old.unlink()
    from PIL import Image
    for i, p in enumerate(imgs):
        im = Image.open(p).convert("RGB")
        im.thumbnail((1600, 1600), Image.LANCZOS)   # big phone photos upload slowly to the free GPUs
        im.save(d / "ref" / (("main" if i == 0 else f"ref{i + 1}") + ".png"))
    refs = sorted(x for x in (d / "ref").glob("*") if x.suffix.lower() in IMG_EXT)
    if not refs:
        raise StudioError("Give at least one photo:  --image <path>")
    say(f"Character '{a.name}': studying the reference photo with Gemini ...", kind="step")
    info = llm.describe_character(refs[:3])
    female = str(info.get("gender", "female")).lower().startswith("f")
    v = {"engine": "gemini", "name": a.voice or ("Sulafat" if female else "Achird"),
         "style": "natural, warm and friendly, conversational Bangladeshi Bangla, like talking to a friend on a phone video",
         "edge_voice": "bn-BD-NabanitaNeural" if female else "bn-BD-PradeepNeural", "allow_edge_fallback": False}
    if not a.no_design:
        say("Designing her/his own Bangla voice (Gemini voice design, free) ...", kind="info")
        try:
            r = voice.design_voice(info.get("voice_design") or "warm friendly Bangladeshi voice", f"studio-{a.name}",
                                   gender="female" if female else "male")
            if r.get("id"):
                v["id"] = r["id"]
                if r.get("sample"):
                    (d / "voice_sample.wav").write_bytes(r["sample"])
                say(f"voice id {r['id']} saved (sample: voice_sample.wav)", kind="ok")
        except Exception as e:  # noqa: BLE001
            say(f"voice design failed ({str(e)[:160]}); using prebuilt voice '{v['name']}'", kind="warn")
    data = {
        "name": a.name, "display_name": a.display or a.name,
        "gender": "female" if female else "male", "age": info.get("age", ""),
        "vibe": info.get("vibe", ""), "address_viewers_as": info.get("address_viewers_as", "আপনারা"),
        "identity": info.get("identity", ""), "outfit": info.get("outfit", ""),
        "settings": info.get("settings", []), "voice": v,
    }
    write_yaml(d / "character.yaml", data, header="# Character bible. Edit freely. identity = what every image prompt must keep.\n"
                                                   "# voice.id = her designed Gemini voice (expires after 1 year unused). voice.name = fallback prebuilt voice.\n")
    say(f"Saved {d / 'character.yaml'}", kind="ok")
    say(f"Listen to {d / 'voice_sample.wav'} . Don't like it? run again, or set voice.name (Leda, Sulafat, Aoede, Achird...) and delete voice.id", kind="info")


# ---------------------------------------------------------------- product
def cmd_product(a):
    from .project import IMG_EXT, list_characters, product_dir, save_project
    d = product_dir(a.slug)
    for sub in ("photos", "inbox", "final", "posters"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    for p in (a.photos or []):
        p = Path(p)
        if p.suffix.lower() not in IMG_EXT:
            raise StudioError(f"Not an image: {p}")
        shutil.copy2(p, d / "photos" / (p.stem + p.suffix.lower().replace(".jfif", ".jpg")))
    f = d / "project.yaml"
    if f.exists() and not a.force:
        say(f"{f} already exists (photos added). Use --force to reset the project file.", kind="warn")
        return
    chars = list_characters()
    pj = {
        "_dir": d, "_slug": a.slug,
        "character": a.character or (chars[0] if chars else "CHANGE_ME"),
        "formats": ["selfie", "greenscreen", "faceless"],
        "script_style": "explainer",
        "product": {"name": a.name or a.slug, "name_bn": "", "short_name": a.name.split()[0] if a.name else a.slug,
                    "what_it_is": a.what or "", "benefits": [], "proof": [], "avoid": [], "audience": "",
                    "hero_photo": "", "broll_photos": [], "no_cutout": []},
        "brand": {"page": a.page or "", "phone": a.phone or "", "show_price": bool(a.price), "price_text": a.price or "",
                  "cta": "অর্ডার করতে এখনই কল করুন" if not a.price else "অর্ডার করতে মেসেজ করুন",
                  "badges": ["ক্যাশ অন ডেলিভারি", "সারা দেশে ডেলিভারি"], "colors": {"primary": ""}},
        "music": "", "voice_speed": 1.08, "caption_style": "pop", "title_style": "white", "sfx": True,
        "scenes": {}, "script": {"hooks": [], "body": [], "cta": {}}, "poster": {}, "ad_copy": {},
    }
    save_project(pj)
    say(f"Created {f}", kind="ok")
    say("Now fill product: what_it_is / benefits / proof / avoid in project.yaml (plain Bangla or English is fine),"
        f" then:  studio write {a.slug}", kind="info")


# ---------------------------------------------------------------- write
def cmd_write(a):
    from . import llm
    from .project import load_character, load_project, save_project
    pj = load_project(a.slug)
    if (pj.get("script") or {}).get("body") and not a.force:
        raise StudioError("This product already has a script. Use --force to replace it (your edits will be lost).")
    ch = load_character(pj["character"])
    say(f"Writing Bangla script + {a.hooks} hooks with Gemini (free) ...", kind="step")
    data = llm.write_script(pj, ch, a.hooks)
    for i, h in enumerate(data["hooks"], 1):
        h["id"] = f"h{i:02d}"
    for i, b in enumerate(data["body"], 1):
        b["id"] = f"b{i:02d}"
    pj["script"] = {"hooks": data["hooks"], "body": data["body"], "cta": data["cta"]}
    scenes = {} if a.force else dict(pj.get("scenes") or {})   # --force replaces the old scene prompts too
    scenes.update({k: v for k, v in data["scenes"].items() if not scenes.get(k)})
    pj["scenes"], pj["poster"], pj["ad_copy"] = scenes, data["poster"], data["ad_copy"]
    save_project(pj)
    say(f"Script saved in {pj['_dir'] / 'project.yaml'}  -> read it, fix any wording, then:  studio make {a.slug}", kind="ok")
    for h in data["hooks"]:
        say(f"{h['id']} [{h.get('pattern')}] {h['say']}", kind="info")
    _policy_check(pj)


def _policy_check(pj):
    from .llm import lint
    warnings = lint(pj)
    if warnings:
        say("Policy check: fix these in project.yaml before running ads", kind="step")
        for w in warnings:
            say(w, kind="warn")
    else:
        say("Policy check: no risky words found", kind="ok")


# ---------------------------------------------------------------- make & steps
def _ctx(a):
    from .project import load_character, load_project
    pj = load_project(a.slug)
    ch = load_character(pj["character"])
    fmts = _csv(getattr(a, "formats", None)) or pj.get("formats") or ["selfie", "faceless"]
    bad = [f for f in fmts if f not in ("selfie", "greenscreen", "faceless")]
    if bad:
        raise StudioError(f"Unknown format(s): {bad}")
    return pj, ch, fmts


ALL_STEPS = ("voice", "scenes", "talk", "build", "posters")


def cmd_make(a, steps=ALL_STEPS):
    """Run the steps in order. Steps not listed only *use* what already exists (no new generation)."""
    from . import pipeline, poster
    from .render import Renderer
    pj, ch, fmts = _ctx(a)
    single = _csv(getattr(a, "engine", None))
    img_eng = _csv(getattr(a, "engine_image", None)) or (single if steps == ("voice", "scenes") else None) \
        or ["qwen", "flux", "manual"]
    talk_eng = _csv(getattr(a, "engine_talk", None)) or (single if steps == ("voice", "talk") else None) \
        or ["ltx", "ltx-mm", "manual"]
    people = any(f in fmts for f in ("selfie", "greenscreen"))
    summary = []
    if getattr(a, "redo_voice", False):
        old = list((pj["_dir"] / "work" / "audio").glob("*.wav"))
        for f in old:
            f.unlink()
        say(f"deleted {len(old)} recorded lines: they will be spoken again", kind="info")
    _policy_check(pj)
    with Renderer() as r:
        say(f"{pj['_slug']}: preparing product cut-outs, colours, end card", kind="step")
        res = pipeline.prepare(pj, r)
        say("voice-over (Gemini TTS)", kind="step")
        pipeline.voices(pj, ch, res, fmts)
        if people or "posters" in steps:
            say("scene images (character + product)", kind="step")
            waiting = pipeline.scenes(pj, ch, res, fmts, img_eng if "scenes" in steps else [],
                                      posters="posters" in steps)
            if waiting:
                summary.append(f"scene images not made yet: {', '.join(waiting)}"
                               + ("  (see inbox/TODO.md)" if "scenes" in steps else f"  (run: studio scenes {pj['_slug']})"))
        if people:
            say("talking clips (LTX-2 lip-sync on the free HF GPU)" if "talk" in steps else "talking clips (existing only)", kind="step")
            report = pipeline.talks(pj, ch, res, fmts, talk_eng if "talk" in steps else [],
                                    max_clips=getattr(a, "max_clips", None))
            if report["quota"]:
                summary.append(report["quota"])
            if report["pending"]:
                more = " ..." if len(report["pending"]) > 6 else ""
                summary.append(f"talking clips still to make: {len(report['pending'])} "
                               f"({', '.join(report['pending'][:6])}{more})  -> run again later: studio make {pj['_slug']}")
        made = []
        if "build" in steps:
            say("assembling videos", kind="step")
            made = pipeline.build(pj, ch, res, fmts, hook_ids=_csv(getattr(a, "hooks", None)),
                                  version=getattr(a, "version", 1) or 1,
                                  allow_missing=getattr(a, "allow_missing", False), renderer=r)
        if "posters" in steps:
            say("posters", kind="step")
            made += poster.render_all(pj, res, templates=_csv(getattr(a, "templates", None)),
                                      sizes=_csv(getattr(a, "sizes", None)) or ("4:5",), renderer=r)
    say("Summary", kind="step")
    say(f"{len(made)} files made -> {pj['_dir'] / 'final'}  and  {pj['_dir'] / 'posters'}", kind="ok")
    from . import voice as _voice
    if _voice.FALLBACK_USED:
        summary.append("Today's free quota for her designed voice was used up, so a similar backup voice spoke some lines. "
                       f"Tomorrow run:  studio make {pj['_slug']} --redo-voice   for her real voice.")
    for s in summary:
        say(s, kind="warn")
    if made:
        say(f"Log them:  studio log {pj['_slug']}", kind="info")


def cmd_step(name):
    steps = {"voice": ("voice",), "scenes": ("voice", "scenes"), "talk": ("voice", "talk"),
             "build": ("voice", "build"), "posters": ("voice", "posters")}[name]

    def run(a):
        if name == "posters":
            return _posters_only(a)
        return cmd_make(a, steps=steps)
    return run


def _posters_only(a):
    """Posters from what exists (no voice, no GPU). Add the poster_hero scene first for the 'hero'/'behind' look."""
    from . import matte, pipeline, poster
    from .project import load_project, work
    from .render import Renderer
    pj = load_project(a.slug)
    with Renderer() as r:
        res = pipeline.prepare(pj, r)
        if res["scenes"].get("poster_hero"):
            res["person_cutout"] = matte.cutout(res["scenes"]["poster_hero"],
                                                work(pj["_slug"], "cutouts") / "poster_hero_person.png")
        made = poster.render_all(pj, res, templates=_csv(a.templates), sizes=_csv(a.sizes) or ("4:5",), renderer=r)
    if not made:
        raise StudioError("No posters made.")


# ---------------------------------------------------------------- status & log
def cmd_status(a):
    from . import pipeline
    from .project import load_project, script_lines
    pj = load_project(a.slug)
    d = pj["_dir"]
    say(f"{a.slug}", kind="step")
    try:
        hooks, body, cta = script_lines(pj)
        say(f"script: {len(hooks)} hooks, {len(body)} body lines, cta {'yes' if cta.get('say') else 'NO'}", kind="ok")
    except StudioError as e:
        say(str(e), kind="warn")
        return
    scenes = sorted(p.stem for p in (d / "work" / "scenes").glob("*.png"))
    say(f"scene images: {', '.join(scenes) or 'none yet'}", kind="info")
    clips = list((d / "work" / "clips").glob("talk_*.mp4"))
    for fmt in ("selfie", "greenscreen"):
        if fmt in (pj.get("formats") or []):
            need = pipeline.talk_lines(pj, fmt)
            have = {c.name.split("_")[1].split("-", 1)[1] for c in clips if c.name.startswith(f"talk_{fmt}-")}
            say(f"{fmt}: talking clips {len(have & {x['id'] for x in need})}/{len(need)}", kind="info")
    finals = sorted((d / "final").rglob("*.mp4"))
    say(f"finished videos: {len(finals)}", kind="ok" if finals else "info")
    for f in finals:
        say(f"{f.relative_to(d)}", kind="info")
    posters = sorted((d / "posters").glob("*.png"))
    say(f"posters: {len(posters)}", kind="ok" if posters else "info")
    todo = d / "inbox" / "TODO.md"
    if todo.exists():
        say(f"manual to-do list: {todo}", kind="warn")


def cmd_log(a):
    from .project import load_project
    pj = load_project(a.slug)
    log = config.ROOT.parent / "03-logs" / "creative-log.md"
    if not log.exists():
        raise StudioError(f"{log} not found")
    text = log.read_text(encoding="utf-8")
    hooks = {h["id"]: h for h in (pj.get("script", {}).get("hooks") or [])}
    rows = []
    for f in sorted((pj["_dir"] / "final").rglob("*.mp4")):
        if f.name in text:
            continue
        m = re.search(r"_(h\d+)_v\d+\.mp4$", f.name)
        pat = hooks.get(m.group(1), {}).get("pattern", "") if m else ""
        fmt = f.parent.name
        tools = {"selfie": "Gemini TTS, Qwen-Image-Edit/FLUX (HF), LTX-2 lip-sync (HF), studio",
                 "greenscreen": "Gemini TTS, Qwen-Image-Edit/FLUX (HF), LTX-2 lip-sync (HF), RVM matte, studio",
                 "faceless": "Gemini TTS, studio (ffmpeg)"}.get(fmt, "studio")
        rows.append(f"| {dt.date.today().isoformat()} | {f.name} | {pj['product'].get('name', pj['_slug'])} | "
                    f"{fmt} | {pat} | {tools} |  | ৳0 (free tiers) | DRAFT |")
    if not rows:
        say("Nothing new to log.", kind="info")
        return
    lines = text.split("\n")
    head = next(i for i, l in enumerate(lines) if l.startswith("| Date | File name |"))
    i = head + 2
    while i < len(lines) and lines[i].startswith("|") and lines[i].replace("|", "").strip():
        i += 1
    while i < len(lines) and lines[i].startswith("|") and not lines[i].replace("|", "").strip():
        lines.pop(i)  # drop the empty placeholder rows
    lines[i:i] = rows
    log.write_text("\n".join(lines), encoding="utf-8")
    say(f"Added {len(rows)} rows to {log}", kind="ok")


# ---------------------------------------------------------------- main
def main(argv=None):
    p = argparse.ArgumentParser(prog="studio", description="Free Bangla UGC video + poster studio", add_help=True)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("help")
    s = sub.add_parser("doctor"); s.add_argument("--test", action="store_true", help="also make one test voice line")
    sub.add_parser("setup")
    s = sub.add_parser("character"); s.add_argument("name"); s.add_argument("--image", nargs="+")
    s.add_argument("--display"); s.add_argument("--voice", help="prebuilt Gemini voice name (default Sulafat/Achird)")
    s.add_argument("--no-design", action="store_true", help="don't design a custom voice")
    s = sub.add_parser("product"); s.add_argument("slug"); s.add_argument("--photos", nargs="+")
    s.add_argument("--name"); s.add_argument("--what"); s.add_argument("--page"); s.add_argument("--phone")
    s.add_argument("--price", help="leave out to never show a price"); s.add_argument("--character")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("write"); s.add_argument("slug"); s.add_argument("--hooks", type=int, default=10)
    s.add_argument("--force", action="store_true")
    for name in ("make", "voice", "scenes", "talk", "build", "posters"):
        s = sub.add_parser(name); s.add_argument("slug"); s.add_argument("--formats")
        s.add_argument("--hooks"); s.add_argument("--engine"); s.add_argument("--engine-image"); s.add_argument("--engine-talk")
        s.add_argument("--max-clips", type=int); s.add_argument("--version", type=int, default=1)
        s.add_argument("--allow-missing", action="store_true"); s.add_argument("--templates"); s.add_argument("--sizes")
        s.add_argument("--redo-voice", action="store_true", help="record all lines again (e.g. after a fallback voice was used)")
    s = sub.add_parser("status"); s.add_argument("slug")
    s = sub.add_parser("log"); s.add_argument("slug")
    a = p.parse_args(argv)
    handlers = {"doctor": cmd_doctor, "setup": cmd_setup, "character": cmd_character, "product": cmd_product,
                "write": cmd_write, "make": cmd_make, "status": cmd_status, "log": cmd_log,
                "voice": cmd_step("voice"), "scenes": cmd_step("scenes"), "talk": cmd_step("talk"),
                "build": cmd_step("build"), "posters": cmd_step("posters")}
    if not a.cmd or a.cmd == "help":
        say(HELP)
        return 0
    try:
        handlers[a.cmd](a)
        return 0
    except StudioError as e:
        say(str(e), kind="err")
        return 1
    except KeyboardInterrupt:
        say("stopped", kind="warn")
        return 130


if __name__ == "__main__":
    sys.exit(main())
