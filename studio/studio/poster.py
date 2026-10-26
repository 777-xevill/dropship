"""Product posters (feed 4:5, square, story) from HTML templates + your real product cut-outs.

Templates (templates/posters/):
  split     dark brand side, floating product copies, white band with stacked headline   (ref: Crystal Clear)
  features  big title + numbered benefit cards + product hero                            (ref: Realme Buds)
  giant     giant vertical word behind the product, two-tone background                   (ref: Matcha)
  hero      your character holding the product, curved white panel + tagline             (ref: Aqua)
  behind    giant word BEHIND the cut-out character/product                              (ref: Apple watch)
  offer     clean page post: product, 3 ticks, call button, trust badges
"""
from pathlib import Path

from .render import Renderer
from .util import say

TEMPLATES = ["split", "features", "giant", "hero", "behind", "offer"]
SIZES = {"4:5": (1080, 1350), "1:1": (1080, 1080), "9:16": (1080, 1920)}


def context(pj: dict, res: dict) -> dict:
    brand, prod, po = pj.get("brand", {}), pj.get("product", {}), pj.get("poster", {})
    show_price = bool(brand.get("show_price"))
    big = (po.get("big_word") or prod.get("short_name") or prod.get("name", "")).strip().split(" ")[0]
    features = [f for f in (po.get("features") or prod.get("benefits") or []) if f][:3]
    badge = po.get("badge") or "ক্যাশ অন ডেলিভারি"
    cta = po.get("cta") or brand.get("cta") or "অর্ডার করতে কল করুন"
    if show_price and brand.get("price_text"):
        badge = brand["price_text"]
    return {
        "c": res["colors"], "product": res["cutouts"][0], "cutouts": res["cutouts"][:3],
        "person": res.get("person_cutout"), "hero_photo": res["scenes"].get("poster_hero"),
        "scene": res["scenes"].get("product_scene"),
        "headline": po.get("headline") or prod.get("name_bn") or prod.get("name", ""),
        "sub": po.get("sub", ""), "features": features, "badge": badge, "cta": cta,
        "phone": brand.get("phone", ""), "page": brand.get("page", ""),
        "brand_name": prod.get("short_name") or prod.get("name", ""),
        "big_word": big, "big_word_latin": big.isascii(),
    }


def render_all(pj: dict, res: dict, templates=None, sizes=("4:5",), renderer: Renderer | None = None) -> list[Path]:
    if renderer is None:
        with Renderer() as r:
            return render_all(pj, res, templates, sizes, r)
    ctx = context(pj, res)
    out_dir = pj["_dir"] / "posters"
    out_dir.mkdir(exist_ok=True)
    made = []
    for t in (templates or TEMPLATES):
        if t not in TEMPLATES:
            say(f"unknown poster template '{t}' (choose from {', '.join(TEMPLATES)})", kind="warn")
            continue
        if t == "hero" and not ctx["hero_photo"]:
            say(f"poster 'hero' skipped: needs the poster_hero scene image (studio scenes {pj['_slug']})", kind="warn")
            continue
        for s in sizes:
            if s not in SIZES:
                say(f"unknown size '{s}' (use 4:5, 1:1 or 9:16)", kind="warn")
                continue
            w, h = SIZES[s]
            out = out_dir / f"{pj['_slug']}_{t}_{w}x{h}.png"
            renderer.template(f"posters/{t}.html", out, w, h, **ctx)
            made.append(out)
            say(f"poster {out.name}", kind="ok")
    return made
