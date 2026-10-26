"""Bangla text helpers: TTS-friendly normalisation and caption chunking."""
import re

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
EN_DIGITS = "0123456789"
_TO_BN = str.maketrans(EN_DIGITS, BN_DIGITS)
_TO_EN = str.maketrans(BN_DIGITS, EN_DIGITS)
DIGIT_WORDS = ["শূন্য", "এক", "দুই", "তিন", "চার", "পাঁচ", "ছয়", "সাত", "আট", "নয়"]

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF️‍⃣]+")
_PHONE = re.compile(r"(?<![\d০-৯])(?:\+?[8৮][8৮][-\s]?)?([0০][1১][3-9৩-৯][\d০-৯]{2})[-\s]?([\d০-৯]{3})[-\s]?([\d০-৯]{3})(?![\d০-৯])")


def to_bn_digits(s: str) -> str:
    return str(s).translate(_TO_BN)


def to_en_digits(s: str) -> str:
    return str(s).translate(_TO_EN)


def strip_emoji(s: str) -> str:
    return re.sub(r"\s{2,}", " ", _EMOJI.sub("", s)).strip()


def _phone_words(m: re.Match) -> str:
    groups = [to_en_digits(g) for g in m.groups()]
    return ", ".join(" ".join(DIGIT_WORDS[int(d)] for d in g) for g in groups)


def speakable(text: str) -> str:
    """Rewrite on-screen style text into something a TTS voice reads naturally in Bangla."""
    t = strip_emoji(text)
    t = _PHONE.sub(_phone_words, t)
    t = re.sub(r"৳\s*([\d০-৯,]+)", r"\1 টাকা", t)
    t = re.sub(r"([\d০-৯]+)\s*%", r"\1 পার্সেন্ট", t)
    t = t.replace("—", ", ").replace("–", ", ").replace("•", ", ").replace("|", ", ")
    t = re.sub(r"\s*,\s*,+", ", ", t)
    return re.sub(r"\s{2,}", " ", t).strip(" ,")


# ---------- caption timing ----------
_BASE = re.compile(r"[অ-ঔক-হৎড়-য়ৠৡ]")
_VIRAMA = "্"


def word_weight(word: str) -> float:
    """Rough spoken length of a word (≈ syllables). Conjuncts count once."""
    bn = len(_BASE.findall(word)) - word.count(_VIRAMA)
    latin = len(re.findall(r"[A-Za-z]", word)) / 2.5
    digits = len(re.findall(r"[\d০-৯]", word)) * 1.2
    return max(1.0, bn + latin + digits)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[।?!])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_phrases(text: str, max_words: int = 3, max_chars: int = 22) -> list[list[str]]:
    """Split a line into caption chunks of a few words, breaking after punctuation when possible."""
    words = strip_emoji(text).split()
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(cur + [w])) > max_chars):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[,।?!:;]$", w) and len(cur) >= 2:
            chunks.append(cur)
            cur = []
    if cur:
        if chunks and len(cur) == 1 and len(chunks[-1]) < max_words:
            chunks[-1].append(cur[0])
        else:
            chunks.append(cur)
    return chunks


def time_words(words: list[str], start: float, end: float) -> list[tuple[str, float, float]]:
    """Spread [start, end] over words in proportion to their spoken weight."""
    weights = [word_weight(w) + 0.35 for w in words]
    total = sum(weights) or 1.0
    out, t = [], start
    for w, wt in zip(words, weights):
        d = (end - start) * wt / total
        out.append((w, t, t + d))
        t += d
    return out
