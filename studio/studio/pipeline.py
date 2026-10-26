"""The production pipeline for one product: prepare -> voice -> scenes -> talk -> build -> posters.
Every step is cached and resumable: re-running only does what is missing."""
from pathlib import Path

from . import assemble, broll, colors, config, hf, images, matte, talk, voice
from .project import photos, script_lines, work
from .render import Renderer
from .util import StudioError, say, sha

FORMATS = ("selfie", "greenscreen", "faceless")
TALK_SIZE = {"selfie": (512, 768), "greenscreen": (384, 576)}
SCENE_ASPECT = {"poster_hero": "4:5", "product_scene": "4:5"}
DEFAULT_SCENES = {
    "selfie_a": "The person from image 1 holding the product from image 2 close to their face with one hand, filming a "
                "casual selfie video with a phone at arm's length, looking into the lens mid-sentence, friendly natural "
                "expression, at home in a tidy Dhaka bedroom with soft window light, vertical 9:16",
    "selfie_b": "The person from image 1 showing the product from image 2 to the camera at chest height, selfie video "
                "angle slightly from the side, on a balcony with plants in morning light, vertical 9:16",
    "greenscreen": "The person from image 1, waist-up, facing the camera and talking with relaxed hands, plain light "
                   "grey studio wall background, even soft light, vertical 9:16",
    "poster_hero": "The person from image 1 holding the product from image 2 out toward the camera with a confident "
                   "smile, clean bright studio background, commercial advertising photo, vertical 4:5",
    "product_scene": "The product from image 2 alone on a styled surface that suits it, premium e-commerce hero photo, "
                     "soft shadows, no people, no text, vertical 4:5",
}


def prepare(pj: dict, renderer: Renderer) -> dict:
    slug = pj["_slug"]
    ph = photos(pj)
    if not ph:
        raise StudioError(f"No product photos in {pj['_dir'] / 'photos'}")
    hero_name = (pj.get("product", {}).get("hero_photo") or "").replace("photos/", "")
    ph.sort(key=lambda p: (p.name != hero_name, p.name))
    cut_dir = work(slug, "cutouts")
    skip = set((pj.get("product", {}).get("no_cutout") or []))
    res = {"photos": ph, "cutouts": []}
    for p in ph[:6]:
        if p.name in skip:
            continue
        res["cutouts"].append(matte.cutout(p, cut_dir / f"{p.stem}_{matte.CUT_VERSION}.png"))
    if not res["cutouts"]:
        raise StudioError("Could not cut out any product photo (set product.no_cutout less aggressively).")
    res["product_ref"] = matte.on_white(res["cutouts"][0], cut_dir / "product_ref_white.jpg")
    res["photos_for_broll"] = [pj["_dir"] / p for p in (pj.get("product", {}).get("broll_photos") or [])
                               if (pj["_dir"] / p).exists()]
    brand = pj.get("brand", {})
    res["colors"] = colors.palette((brand.get("colors") or {}).get("primary"), res["cutouts"][0])
    res["scenes"] = {p.stem: p for p in work(slug, "scenes").glob("*.png")}
    ov = work(slug, "overlays")
    c = res["colors"]
    tpl = config.TEMPLATES / "overlays"
    for key, lay in (("stage", "full"), ("stage_gs", "gs")):
        cy = broll.LAYOUTS[lay]["cy"]
        pod = broll.LAYOUTS[lay]["max_h"] * 0.44
        stage = ov / f"{key}_{sha(c, cy, tpl / 'stage.html')}.png"
        if not stage.exists():
            renderer.template("overlays/stage.html", stage, 1080, 1920, c=c, cy=cy, pod=pod)
        res[key] = stage
    cta = pj.get("script", {}).get("cta", {}) or {}
    end_title = cta.get("text") or brand.get("cta") or "অর্ডার করতে কল করুন"
    badges = brand.get("badges") or ["ক্যাশ অন ডেলিভারি", "সারা দেশে ডেলিভারি"]
    endcard = ov / f"endcard_{sha(c, end_title, brand.get('phone'), brand.get('page'), badges, res['cutouts'][0], tpl / 'endcard.html')}.png"
    if not endcard.exists():
        renderer.template("overlays/endcard.html", endcard, 1080, 1920, c=c, title=end_title, page=brand.get("page"),
                          phone=brand.get("phone"), button=brand.get("button_text"), badges=badges,
                          product=res["cutouts"][0])
    res["endcard"] = endcard
    res["music"] = assemble.pick_music(pj)
    res["seg_cache"] = work(slug, "segments")
    res["build_dir"] = work(slug, "build")
    res["clips"], res["masks"] = {}, {}
    return res


def talk_lines(pj: dict, fmt: str) -> list[dict]:
    hooks, body, _ = script_lines(pj)
    if fmt == "selfie":
        return [b for b in body if (b.get("visual") or "talk") == "talk"] + [h for h in hooks if (h.get("visual") or "talk") == "talk"]
    if fmt == "greenscreen":
        return list(body) + list(hooks)
    return []


def voices(pj: dict, ch: dict, res: dict, fmts) -> None:
    hooks, body, cta = script_lines(pj)
    d = work(pj["_slug"], "audio")
    talking = {ln["id"] for f in fmts for ln in talk_lines(pj, f)}
    res["audio"] = {}
    groups = [
        ([(h["id"], h["say"]) for h in hooks], "energetic, catchy opening line"),
        ([(b["id"], b["say"]) for b in body] + ([("cta", cta["say"])] if cta.get("say") else []), ""),
    ]
    for items, mood in groups:
        if not items:
            continue
        got = voice.synth_many(items, d, ch, mood=mood)   # one free TTS request per group
        speed = float(pj.get("voice_speed", 1.08))        # UGC editors speed speech up a little
        for key, _text in items:
            a = voice.speed_up(got[key], speed)
            if key in talking:
                a, _bucket = talk.squeeze_for_clip(a)
            res["audio"][key] = a
        say(f"voice: {len(items)} lines ready", kind="ok")


def scenes(pj: dict, ch: dict, res: dict, fmts, engines, posters: bool) -> list[str]:
    hooks, body, _ = script_lines(pj)
    need = []   # most important first: free GPU quota may run out part-way
    if "selfie" in fmts:
        need.append("selfie_a")
    if "greenscreen" in fmts:
        need.append("greenscreen")
    if "selfie" in fmts and len(talk_lines(pj, "selfie")) > 2:
        need.append("selfie_b")
    if posters:
        need.append("poster_hero")
    for ln in hooks + body:
        v = (ln.get("visual") or "")
        if v.startswith("scene:"):
            need.append(v.split(":", 1)[1].strip())
    refs = [ch["_refs"][0], res["product_ref"]]
    out_dir = work(pj["_slug"], "scenes")
    waiting = []
    for name in dict.fromkeys(need):
        prompt = (pj.get("scenes") or {}).get(name) or DEFAULT_SCENES.get(name)
        if not prompt:
            raise StudioError(f"No prompt for scene '{name}'. Add it under scenes: in project.yaml")
        p = images.make_image(name, prompt, refs, out_dir / f"{name}.png", pj,
                              aspect=SCENE_ASPECT.get(name, "9:16"), engines=engines)
        if p:
            res["scenes"][name] = p
        else:
            waiting.append(name)
    if res["scenes"].get("poster_hero"):
        res["person_cutout"] = matte.cutout(res["scenes"]["poster_hero"], work(pj["_slug"], "cutouts") / "poster_hero_person.png")
    return waiting


def talks(pj: dict, ch: dict, res: dict, fmts, engines, max_clips: int | None = None) -> dict:
    """Make talking clips (body first: it is shared by every variant). Stops cleanly when free quota runs out."""
    clip_dir = work(pj["_slug"], "clips")
    mask_dir = work(pj["_slug"], "masks")
    jobs = []
    for fmt in fmts:
        if fmt not in TALK_SIZE:
            continue
        lines = talk_lines(pj, fmt)
        for i, ln in enumerate(lines):
            if fmt == "selfie":
                img = res["scenes"].get("selfie_b") if (i % 2 == 1 and res["scenes"].get("selfie_b")) else res["scenes"].get("selfie_a")
            else:
                img = res["scenes"].get("greenscreen")
            jobs.append((fmt, ln, img))
    report = {"done": 0, "made": 0, "pending": [], "quota": None}
    for fmt, ln, img in jobs:
        key = (fmt, ln["id"])
        if img is None:
            report["pending"].append(f"{fmt}:{ln['id']} (scene image missing)")
            continue
        tag = f"{fmt}-{ln['id']}"
        existing = talk.clip_path(tag, img, res["audio"][ln["id"]], clip_dir)
        stop = report["quota"] or (max_clips is not None and report["made"] >= max_clips)
        if stop and not existing.exists():
            report["pending"].append(f"{fmt}:{ln['id']}")
            continue
        was_there = existing.exists()
        try:
            clip = talk.make_clip(tag, img, res["audio"][ln["id"]], clip_dir, pj, ch,
                                  engines=engines, size=TALK_SIZE[fmt])
        except hf.QuotaError as e:
            report["quota"] = str(e)
            report["pending"].append(f"{fmt}:{ln['id']}")
            continue
        except StudioError as e:
            report["pending"].append(f"{fmt}:{ln['id']} (failed: {str(e)[:80]})")
            continue
        if clip is None:
            report["pending"].append(f"{fmt}:{ln['id']}" + (" (manual, see inbox/TODO.md)" if "manual" in engines else ""))
            continue
        report["made"] += 0 if was_there else 1
        report["done"] += 1
        res["clips"][key] = clip
        if fmt == "greenscreen":
            res["masks"][key] = matte.video_matte(clip, mask_dir / f"{clip.stem}_mask.mp4")
    return report


def build(pj: dict, ch: dict, res: dict, fmts, hook_ids=None, version: int = 1,
          allow_missing: bool = False, renderer: Renderer = None) -> list[Path]:
    hooks, body, cta = script_lines(pj)
    if hook_ids:
        hooks = [h for h in hooks if h["id"] in hook_ids]
    letter = pj.get("template")
    made = []
    for fmt in fmts:
        needs = {ln["id"] for ln in talk_lines(pj, fmt)}
        missing_body = [b["id"] for b in body if b["id"] in needs and (fmt, b["id"]) not in res["clips"]]
        if missing_body and not allow_missing:
            say(f"{fmt}: skipped, talking clips still missing for {', '.join(missing_body)} "
                f"(run  studio talk {pj['_slug']}  tomorrow, or add --allow-missing to use product shots instead)", kind="warn")
            continue
        for h in hooks:
            if h["id"] in needs and (fmt, h["id"]) not in res["clips"] and not allow_missing:
                say(f"{fmt}/{h['id']}: skipped, hook clip not made yet", kind="warn")
                continue
            name = f"{pj['_slug']}_{letter or assemble.TEMPLATE_LETTER[fmt]}_{h['id']}_v{version}.mp4"
            out = pj["_dir"] / "final" / fmt / name
            say(f"building {fmt}/{name} ...", kind="info")
            assemble.build_variant(pj, fmt, h, body, cta, res, out, renderer)
            made.append(out)
            say(f"{out.relative_to(pj['_dir'])}", kind="ok")
    return made
