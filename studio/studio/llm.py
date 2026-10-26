"""Gemini text model (free tier): character description and Bangla UGC scripts."""
import json
import mimetypes
import re
import time
from pathlib import Path

from . import config
from .util import StudioError, say

_client = None


def client():
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise StudioError("GEMINI_API_KEY missing. Put it in studio/.env  (free key: https://aistudio.google.com/apikey)")
        from google import genai
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _image_part(path: Path):
    from google.genai import types
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    if path.suffix.lower() == ".jfif":
        mime = "image/jpeg"
    return types.Part.from_bytes(data=Path(path).read_bytes(), mime_type=mime)


def generate_json(prompt: str, images: list[Path] = (), temperature: float = 0.9) -> dict:
    parts = [_image_part(p) for p in images] + [prompt]
    last = None
    for model in config.TEXT_MODELS:
        for attempt in range(4):
            try:
                r = client().models.generate_content(
                    model=model, contents=parts,
                    config={"response_mime_type": "application/json", "temperature": temperature})
                text = (r.text or "").strip()
                text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
                return json.loads(text)
            except json.JSONDecodeError as e:
                last = e
                continue
            except Exception as e:  # noqa: BLE001 - surface API errors with context
                last = e
                msg = str(e)
                if "404" in msg or "not found" in msg.lower() or "not supported" in msg.lower():
                    break  # try next model
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "503" in msg or "UNAVAILABLE" in msg:
                    wait = 20 * (attempt + 1)
                    say(f"Gemini busy/limited ({model}), retrying in {wait}s", kind="warn")
                    time.sleep(wait)
                    continue
                raise StudioError(f"Gemini error ({model}): {msg[:400]}") from e
    raise StudioError(f"Gemini text generation failed: {str(last)[:400]}")


# ---------------- character ----------------
def describe_character(images: list[Path]) -> dict:
    prompt = """You are building a character bible for an AI UGC presenter who will appear in many ads.
Look at the reference photo(s) of ONE person and return JSON with exactly these keys:
{
 "identity": "60-90 words, English, ONLY permanent physical traits a model needs to redraw the same person: apparent age range, gender presentation, skin tone, face shape, eyes, eyebrows, nose, lips, hair colour/length/style, distinctive marks, body build. No clothes, no background.",
 "outfit": "the outfit in the photo, 10-20 words, English",
 "vibe": "3-6 words, the impression she/he gives on camera",
 "gender": "female|male",
 "age": "e.g. early 30s",
 "voice_design": "English description for designing a matching Bangla TTS voice: gender, age, pitch, warmth, energy, pace, Bangladeshi (Dhaka) accent, how they sound on a phone video",
 "settings": ["3 believable places in a Dhaka home or neighbourhood where this person would film selfie videos, English, 8-14 words each"],
 "address_viewers_as": "Bangla word this presenter would use to address viewers, e.g. আপু / ভাইয়া / বন্ধুরা"
}"""
    return generate_json(prompt, images, temperature=0.4)


# ---------------- scripts ----------------
HOOK_PATTERNS = [
    ("problem_callout", "name a common pain in general terms (never 'you have X')"),
    ("curiosity_gap", "say something incomplete that makes people want the rest"),
    ("before_after", "describe a quick contrast; visual does the work"),
    ("price_shock", "anchor high, reveal low (ONLY if price may be shown)"),
    ("social_proof", "drop into a reaction, e.g. 'everyone was asking about this'"),
    ("demonstration", "start doing/showing the thing immediately"),
    ("objection_first", "lead with the doubt viewers already have"),
    ("us_vs_them", "old way vs this way"),
    ("specific_number", "'3 things...' / '2 reasons...'"),
    ("pattern_break", "unexpected line or moment that stops the thumb"),
]


def write_script(pj: dict, ch: dict, n_hooks: int = 10) -> dict:
    prod, brand = pj.get("product", {}), pj.get("brand", {})
    show_price = bool(brand.get("show_price"))
    patterns = [p for p in HOOK_PATTERNS if show_price or p[0] != "price_shock"]
    style = pj.get("script_style", "explainer")
    persona = {
        "name": ch.get("display_name") or ch.get("name"),
        "gender": ch.get("gender", "female"),
        "age": ch.get("age", ""),
        "vibe": ch.get("vibe", ""),
        "addresses_viewers_as": ch.get("address_viewers_as", "আপনারা"),
        "settings": ch.get("settings", []),
    }
    facts = {k: prod.get(k) for k in ("name", "name_bn", "what_it_is", "benefits", "proof", "avoid", "audience") if prod.get(k)}
    prompt = f"""You are a top Bangladeshi performance-marketing copywriter. Write a UGC-style Facebook/Instagram Reels ad
in natural spoken Bangladeshi Bangla (Dhaka চলিত ভাষা, the way people really talk to a phone camera).

PRESENTER (an AI character who appears in every ad): {json.dumps(persona, ensure_ascii=False)}
PRODUCT FACTS (only claim what is here): {json.dumps(facts, ensure_ascii=False)}
BRAND: page "{brand.get('page', '')}", phone "{brand.get('phone', '')}", show price: {show_price}{', price: ' + str(brand.get('price_text')) if show_price and brand.get('price_text') else ''}
CALL TO ACTION RULE: {brand.get('cta') or 'invite people to call or send a message'}{' — NEVER mention any price or amount of money anywhere.' if not show_price else ''}
STYLE: {style}. {'The presenter explains and recommends like a knowledgeable friend. She NEVER claims personal experience she cannot have (no "আমি ব্যবহার করে দেখেছি", no made-up results or reviews).' if style == 'explainer' else 'Testimonial style, but only claims that are true and provided in the facts.'}

HARD RULES (Meta ad policy + honesty):
- Never assert or imply the viewer's personal attributes, health or body problems ("আপনার কি ... সমস্যা?" is banned). Talk in general terms or first person.
- Never use these words or ideas: নিরাপদ, সেফ, ১০০%, গ্যারান্টি, সেরা, নিশ্চিত ফল, ডাক্তার পরামর্শিত, পার্শ্বপ্রতিক্রিয়া নেই, চিরতরে, অলৌকিক.
- No cure/medical claims, no fake urgency ("আজই শেষ"), no fake numbers or reviews, no sexual or suggestive wording.
- Respect everything listed under "avoid" in the product facts.
- Common English words people use in Bangla are fine (ডেলিভারি, অর্ডার, ফ্রেশ), but no ad-speak.
- Every spoken line ("say") is ONE short sentence of 5-11 words that takes 2.5-4.5 seconds to say.
- The whole ad (hook + body + cta) must stay under 28 seconds, so keep the body tight.
- Write numbers in Bangla digits. Do not use emoji in "say".
- If more hooks are requested than patterns exist, reuse a pattern with a clearly different angle.

RETURN JSON with exactly these keys:
{{
 "hooks": [{n_hooks} items, each from a DIFFERENT pattern in this list: {json.dumps(patterns, ensure_ascii=False)}
    each item: {{"id": "h01".., "pattern": "<pattern key>", "say": "spoken hook, max 2.5 seconds", "text": "on-screen hook title, max 6 words, may differ from say", "visual": "talk" or "product"}}],
 "body": [4-6 items (total spoken words of hook+body+cta under 70), same for every variant, story: relatable situation -> product reveal -> 2-3 concrete benefits/demo -> trust (delivery / pay on delivery / real product) ;
    each: {{"id": "b01".., "say": "...", "visual": "talk" or "product", "text": "optional short on-screen chip (max 4 words) or empty"}}
    first body item visual=talk, at least two items visual=product],
 "cta": {{"say": "spoken call to action, 1 sentence", "text": "end-card text, max 6 words"}},
 "scenes": {{  (English image-edit prompts. ALWAYS call the presenter "the person from image 1" and the product "the product from image 2".
               Never describe the person's face, body or skin: identity comes from the photo. Describe pose, framing, setting, light, and outfit = "{ch.get('outfit', 'the same outfit')}")
   "selfie_a": "the person from image 1 holding the product from image 2 close to her face, filming a casual selfie video with her phone at arm's length, looking into the lens, natural expression mid-sentence, in <one of the presenter settings>, soft natural light, realistic smartphone photo, vertical 9:16",
   "selfie_b": "same person + product, a different setting from the list and a slightly different angle/pose",
   "greenscreen": "the person from image 1, waist-up, talking to camera with relaxed hand gestures, plain light grey studio wall background, even soft light, realistic, vertical 9:16",
   "poster_hero": "the person from image 1 holding the product from image 2 out toward the camera with a confident smile, clean bright studio background in the product's colours, commercial photo, vertical 4:5",
   "product_scene": "the product from image 2 alone, styled on a surface that fits it, premium e-commerce hero shot, soft shadows, no text, vertical 4:5"
 }},
 "poster": {{"headline": "max 5 Bangla words, punchy", "sub": "max 10 words", "features": ["3 items, max 4 words each"], "badge": "max 3 words, e.g. ক্যাশ অন ডেলিভারি", "big_word": "ONE short word (Bangla or English) for giant background typography", "cta": "max 5 words"}},
 "ad_copy": {{"primary_text": "Bangla Facebook ad primary text: hook line, 3-4 lines starting with ✔, then the CTA line", "headline": "max 40 characters"}}
}}"""
    data = generate_json(prompt, temperature=0.95)
    for key in ("hooks", "body", "cta", "scenes", "poster", "ad_copy"):
        if key not in data:
            raise StudioError(f"Script generator returned no '{key}'. Run the command again.")
    return data


# ---------------- policy check ----------------
RISKY = ["নিরাপদ", "সেফ", "১০০%", "100%", "গ্যারান্টি", "সেরা", "নিশ্চিত ফল", "ডাক্তার", "পার্শ্বপ্রতিক্রিয়া",
         "চিরতরে", "অলৌকিক", "আজই শেষ", "অরিজিনাল", "জাপানি", "সেক্স", "সহবাস", "যৌন", "তৃপ্তি", "সময় বাড়"]
_PERSONAL = ["আপনার কি", "আপনি কি ভুগছেন", "আপনার সমস্যা", "আপনার শরীর"]
_PRICE = r"[৳$]\s*[\d০-৯]|[\d০-৯][\d০-৯,]*\s*(?:টাকা|tk\b|taka)"   # an amount, not the phrase "পণ্য দেখে টাকা দিন"


def lint(pj: dict) -> list[str]:
    """Words that can get an ad rejected (Meta) or break your own rules. Returns human-readable warnings."""
    out = []
    s = pj.get("script") or {}
    show_price = bool((pj.get("brand") or {}).get("show_price"))
    items = [("hook " + h.get("id", "?"), h) for h in s.get("hooks") or []] + \
            [("body " + b.get("id", "?"), b) for b in s.get("body") or []] + [("cta", s.get("cta") or {})]
    extra = [w.strip() for a in ((pj.get("product") or {}).get("avoid") or []) for w in re.split(r"[/,;]", str(a))
             if w.strip() and not w.strip().isascii() and len(w.strip()) < 25]
    for where, it in items:
        for field in ("say", "text"):
            t = str(it.get(field) or "")
            for w in RISKY + extra:
                if w and w in t:
                    out.append(f"{where}.{field}: '{w}' -> risky/banned claim: {t}")
            for w in _PERSONAL:
                if w in t:
                    out.append(f"{where}.{field}: talks about the viewer's own problem ('{w}') -> Meta personal-attributes rule: {t}")
            if not show_price and re.search(_PRICE, t, re.I):
                out.append(f"{where}.{field}: mentions money/price but brand.show_price is false: {t}")
    return out
