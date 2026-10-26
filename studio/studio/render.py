"""HTML/CSS -> PNG with the Edge browser already installed on Windows (via Playwright, no download).

Why HTML: AI image models still misspell Bangla. Here every letter is real text in a real Bangla font,
so titles, prices, phone numbers and posters are always correct and sharp.
"""
import base64
import mimetypes
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from . import config
from .util import StudioError

FONT_FACES = [
    ("Anek Bangla", "AnekBangla-VF.ttf", "100 800"),
    ("Hind Siliguri", "HindSiliguri-Regular.ttf", "400"),
    ("Hind Siliguri", "HindSiliguri-Medium.ttf", "500"),
    ("Hind Siliguri", "HindSiliguri-SemiBold.ttf", "600"),
    ("Hind Siliguri", "HindSiliguri-Bold.ttf", "700"),
    ("Noto Sans Bengali", "NotoSansBengali-VF.ttf", "100 900"),
    ("Noto Serif Bengali", "NotoSerifBengali-VF.ttf", "100 900"),
    ("Baloo Da 2", "BalooDa2-VF.ttf", "400 800"),
    ("Galada", "Galada-Regular.ttf", "400"),
    ("Tiro Bangla", "TiroBangla-Regular.ttf", "400"),
    ("Anton", "Anton-Regular.ttf", "400"),
    ("Bebas Neue", "BebasNeue-Regular.ttf", "400"),
    ("Poppins", "Poppins-Regular.ttf", "400"),
    ("Poppins", "Poppins-Medium.ttf", "500"),
    ("Poppins", "Poppins-SemiBold.ttf", "600"),
    ("Poppins", "Poppins-Bold.ttf", "700"),
    ("Poppins", "Poppins-ExtraBold.ttf", "800"),
    ("Poppins", "Poppins-Black.ttf", "900"),
    ("Montserrat", "Montserrat-VF.ttf", "100 900"),
    ("Playfair Display", "PlayfairDisplay-VF.ttf", "400 900"),
]


def font_css() -> Markup:
    rules = []
    for fam, file, weight in FONT_FACES:
        p = config.FONTS / file
        if p.exists():
            rules.append(f"@font-face{{font-family:'{fam}';src:url('{p.as_uri()}');font-weight:{weight};font-display:block}}")
    return Markup("\n".join(rules))   # Markup: Jinja must not HTML-escape the quotes inside CSS


def data_uri(path) -> str:
    """Embed an image file in HTML (works regardless of where the HTML lives)."""
    if not path:
        return ""
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


FIT_JS = """() => {
  // <span data-fit="900" data-fit-max="400">WORD</span> -> largest font-size (<= max) whose text is <= 900px wide.
  // offsetWidth ignores CSS transforms, so this also works for rotated (vertical) words.
  for (const el of document.querySelectorAll('[data-fit]')) {
    const target = parseFloat(el.dataset.fit), max = parseFloat(el.dataset.fitMax || 600);
    el.style.whiteSpace = 'nowrap';
    el.style.display = 'inline-block';
    let lo = 8, hi = max;
    for (let i = 0; i < 20; i++) {
      const mid = (lo + hi) / 2;
      el.style.fontSize = mid + 'px';
      if (el.offsetWidth <= target) lo = mid; else hi = mid;
    }
    el.style.fontSize = lo + 'px';
  }
  return true;
}"""

_env = None


def env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(str(config.TEMPLATES)), autoescape=select_autoescape(["html"]))
        _env.globals["font_css"] = font_css
        _env.filters["img"] = data_uri
    return _env


class Renderer:
    """Keep one headless Edge open while rendering many PNGs."""

    def __enter__(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise StudioError("playwright missing: run  studio setup") from e
        self._pw = sync_playwright().start()
        last = None
        for channel in ("msedge", "chrome", None):
            try:
                self._b = self._pw.chromium.launch(channel=channel, headless=True) if channel else self._pw.chromium.launch(headless=True)
                break
            except Exception as e:  # noqa: BLE001
                last = e
        else:
            self._pw.stop()
            raise StudioError(f"No Edge/Chrome found for rendering: {last}")
        return self

    def __exit__(self, *a):
        self._b.close()
        self._pw.stop()

    def html(self, html: str, out: Path, w: int, h: int, transparent: bool = False) -> Path:
        # Load from a real file: a page made with set_content() is not allowed to read file:// fonts,
        # and Chrome would silently fall back to system fonts.
        src = config.tmpdir("render") / f"page_{abs(hash(html)) % 10**12}.html"
        src.write_text(html, encoding="utf-8")
        page = self._b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        try:
            page.goto(src.as_uri(), wait_until="load")
            fonts = page.evaluate("""async () => { await document.fonts.ready;
                const s = {loaded: 0, error: []}; for (const f of document.fonts) {
                  if (f.status === 'loaded') s.loaded++; if (f.status === 'error') s.error.push(f.family); } return s; }""")
            if fonts["error"] or (fonts["loaded"] == 0 and "@font-face" in html):
                raise StudioError(f"Fonts did not load (errors: {fonts['error']}) - check assets/fonts")
            page.evaluate(FIT_JS)
            page.wait_for_timeout(60)
            out.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out), omit_background=transparent, clip={"x": 0, "y": 0, "width": w, "height": h})
        finally:
            page.close()
            src.unlink(missing_ok=True)
        return out

    def template(self, name: str, out: Path, w: int, h: int, transparent: bool = False, **ctx) -> Path:
        html = env().get_template(name).render(W=w, H=h, **ctx)
        return self.html(html, out, w, h, transparent)
