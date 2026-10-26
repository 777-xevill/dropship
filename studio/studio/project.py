"""Characters and product projects on disk.

characters/<name>/character.yaml   who the presenter is + her voice (shared by every product)
characters/<name>/ref/             reference photos of the presenter (the identity lock)
products/<slug>/project.yaml       script, hooks, brand, scene prompts  (you edit this)
products/<slug>/photos/            your real product photos
products/<slug>/inbox/             drop files made by hand in web tools here
products/<slug>/work/              generated intermediates (safe to delete)
products/<slug>/final/             finished videos
products/<slug>/posters/           finished posters
"""
from pathlib import Path

import yaml

from . import config
from .util import StudioError

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".jfif", ".bmp"}
VID_EXT = {".mp4", ".mov", ".webm", ".mkv"}


def read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(path: Path, data: dict, header: str = "") -> None:
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
    path.write_text(header + text, encoding="utf-8")


# ---------------- characters ----------------
def character_dir(name: str) -> Path:
    return config.CHARACTERS / name


def load_character(name: str) -> dict:
    d = character_dir(name)
    f = d / "character.yaml"
    if not f.exists():
        raise StudioError(f"Character '{name}' not found. Create it first:  studio character {name} --image <photo>")
    ch = read_yaml(f)
    ch["_dir"] = d
    ch["_refs"] = sorted(p for p in (d / "ref").glob("*") if p.suffix.lower() in IMG_EXT)
    if not ch["_refs"]:
        raise StudioError(f"Character '{name}' has no reference photo in {d / 'ref'}")
    return ch


def list_characters() -> list[str]:
    return sorted(p.parent.name for p in config.CHARACTERS.glob("*/character.yaml") if not p.parent.name.startswith("_"))


# ---------------- products ----------------
def product_dir(slug: str) -> Path:
    return config.PRODUCTS / slug


def work(slug: str, *sub: str) -> Path:
    d = product_dir(slug) / "work"
    for s in sub:
        d = d / s
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_project(slug: str) -> dict:
    d = product_dir(slug)
    f = d / "project.yaml"
    if not f.exists():
        raise StudioError(f"Product '{slug}' not found. Create it first:  studio product {slug} --photos <files>")
    pj = read_yaml(f)
    pj["_dir"] = d
    pj["_slug"] = slug
    pj.setdefault("brand", {})
    pj.setdefault("product", {})
    pj.setdefault("script", {})
    pj.setdefault("scenes", {})
    pj.setdefault("poster", {})
    return pj


def save_project(pj: dict) -> None:
    data = {k: v for k, v in pj.items() if not k.startswith("_")}
    write_yaml(pj["_dir"] / "project.yaml", data, header=PROJECT_HEADER)


def photos(pj: dict) -> list[Path]:
    d = pj["_dir"] / "photos"
    return sorted(p for p in d.glob("*") if p.suffix.lower() in IMG_EXT)


def script_lines(pj: dict) -> tuple[list[dict], list[dict], dict]:
    s = pj.get("script") or {}
    hooks = [h for h in (s.get("hooks") or []) if (h or {}).get("say")]
    body = [b for b in (s.get("body") or []) if (b or {}).get("say")]
    cta = s.get("cta") or {}
    if not body:
        raise StudioError(f"No script yet for '{pj['_slug']}'. Run:  studio write {pj['_slug']}   (or fill script: in project.yaml)")
    return hooks, body, cta


def inbox_file(pj: dict, stem: str, kinds=IMG_EXT | VID_EXT) -> Path | None:
    """A file the user dropped into inbox/ named like the item (e.g. scene_selfie_a.png, talk_b01.mp4)."""
    for p in sorted((pj["_dir"] / "inbox").glob(f"{stem}.*")):
        if p.suffix.lower() in kinds:
            return p
    return None


def todo_done(pj: dict, item: str) -> None:
    """Remove a finished item ('scene_selfie_a', 'talk_selfie-b01') from inbox/TODO.md and its upload files."""
    import re
    inbox = pj["_dir"] / "inbox"
    todo = inbox / "TODO.md"
    if todo.exists():
        text = todo.read_text(encoding="utf-8")
        new = re.sub(rf"\n## {re.escape(item)} .*?(?=\n## |\Z)", "", text, flags=re.S)
        if new != text:
            if "\n## " in new:
                todo.write_text(new, encoding="utf-8")
            else:
                todo.unlink()
    stem = item.split("_", 1)[1] if item.startswith("scene_") else item
    up = inbox / "upload_these"
    for f in up.glob(f"{stem}_ref*") if item.startswith("scene_") else up.glob(f"{stem}.*"):
        f.unlink(missing_ok=True)
    if up.exists() and not any(up.iterdir()):
        up.rmdir()


PROJECT_HEADER = """\
# ============================================================================
#  STUDIO PROJECT FILE  -  edit freely (Bangla is fine). Re-run the commands after editing.
#  script.hooks : first 2-3 seconds. Each hook = one video variant.
#  script.body  : the same for every variant.  visual: talk | product | photo:<file> | scene:<name>
#  scenes       : English prompts for the AI images of your character with this product.
#  brand.show_price: false  ->  no price anywhere; CTA asks people to call.
# ============================================================================
"""
