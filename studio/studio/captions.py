"""Burned-in Bangla captions (ASS subtitles rendered by libass/HarfBuzz inside ffmpeg).

Each spoken line is cut into 2-3 word phrases; the word being spoken is highlighted.
"""
from pathlib import Path

from .bangla import split_phrases, strip_emoji, time_words

STYLES = {
    #        font            size  text       outline   outl  shadow  highlight
    "pop":   ("Hind Siliguri", 78, "FFFFFF", "000000", 7.0, 0.0, "FFE14D"),
    "clean": ("Hind Siliguri", 70, "FFFFFF", "000000", 3.0, 2.5, None),
    "box":   ("Hind Siliguri", 66, "FFFFFF", "000000", 14.0, 0.0, "FFE14D"),
}


def _ass_color(hex6: str, alpha: str = "00") -> str:
    hex6 = hex6.lstrip("#")
    return f"&H{alpha}{hex6[4:6]}{hex6[2:4]}{hex6[0:2]}"


def _ov(hex6: str) -> str:
    """Colour for an inline override tag: &HBBGGRR& (no alpha)."""
    hex6 = hex6.lstrip("#")
    return f"&H{hex6[4:6]}{hex6[2:4]}{hex6[0:2]}&"


def _t(sec: float) -> str:
    sec = max(0.0, sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _clean(w: str) -> str:
    return strip_emoji(w).replace("{", "(").replace("}", ")").replace("\\", "")


def build(units: list[tuple[str, float, float]], out: Path, *, y: int = 1240, style: str = "pop",
          max_words: int = 3, highlight: str | None = None) -> Path:
    """units = [(spoken text, start, end), ...] on the final timeline (seconds)."""
    font, size, fg, ol, olw, shw, hl = STYLES.get(style, STYLES["pop"])
    hl = (highlight or hl)
    border_style = 3 if style == "box" else 1
    back = _ass_color("000000", "60") if style == "box" else _ass_color("000000", "80")
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 0",
        "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{font},{size},{_ass_color(fg)},{_ass_color(fg)},{_ass_color(ol)},{back},-1,0,0,0,100,100,0,0,"
        f"{border_style},{olw},{shw},5,70,70,0,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for text, start, end in units:
        phrases = split_phrases(text, max_words=max_words)
        words = [w for ph in phrases for w in ph]
        if not words:
            continue
        timed = time_words(words, start, end)
        k = 0
        for ph in phrases:
            seg = timed[k:k + len(ph)]
            k += len(ph)
            p_start, p_end = seg[0][1], seg[-1][2]
            for i, (_w, ws, we) in enumerate(seg):
                parts = []
                for j, (w2, _a, _b) in enumerate(seg):
                    w2 = _clean(w2)
                    if hl and j == i:
                        parts.append(f"{{\\c{_ov(hl)}}}{w2}{{\\c{_ov(fg)}}}")
                    else:
                        parts.append(w2)
                pop = "\\fscx86\\fscy86\\t(0,90,\\fscx100\\fscy100)" if i == 0 else ""
                s_t = p_start if i == 0 else ws
                e_t = p_end if i == len(seg) - 1 else we
                if not hl:  # one event per phrase
                    if i:
                        continue
                    e_t = p_end
                lines.append(f"Dialogue: 0,{_t(s_t)},{_t(e_t)},Cap,,0,0,0,,{{\\an5\\pos(540,{y}){pop}}}{' '.join(parts)}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
