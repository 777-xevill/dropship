# Free AI UGC stack: research notes (checked 2026-10-15)

Goal: videos like `ugc1.mp4` (green-screen explainer) and `ugc2.mp4` (selfie holding product), posters like
`poster-page/`, one consistent character, Bangla voice, **৳0**, no watermark, on this PC
(RTX 3050 8 GB, 10 GB RAM, C: almost full).

What the reference videos are: `ugc1` = a real creator using TikTok's green-screen effect (cut-out over b-roll,
title box, phrase captions). `ugc2` = an AI avatar: one image of a person holding the product, animated by an
audio-driven model (lip-sync + hand motion; the label text drifts, the giveaway).

**"Tested"** = I ran it on this machine today. Everything else is from the source linked, and free limits change often.

---

## 1. Bangla voice → Gemini 3.8 Flash TTS (free) ✅ tested

| Option | Free? | Bangla quality | Verdict |
|---|---|---|---|
| **Gemini 3.8 Flash TTS** (`gemini-3.8-flash-tts`) | Free tier, **10 requests/day per model** (tested: quota id `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, value 10) | Whisper transcribed the test line almost word-for-word | **Use** |
| Gemini voice design (custom voice) | Worked on the free tier (tested) | Unique persistent voice per character, kept 1 year after last use | **Use** (= voice consistency) |
| Gemini 3.8 Flash-Lite / 3.1 / 2.5 TTS | Free, separate daily quotas | Good; designed voices only on 3.8 | Automatic fallbacks |
| edge-tts `bn-BD-NabanitaNeural` | Free, no key | Whisper could not transcribe it; flatter | Last-resort fallback |

Free-tier detail: Google may use free-tier inputs to improve products, so don't send private data. Ad scripts are fine.
Because of the 10/day cap, the studio speaks all lines in **one request** and cuts at the pauses (tested: 7 lines in one call,
every segment transcribed to exactly its sentence).
Sources: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) ·
[Speech generation docs](https://ai.google.dev/gemini-api/docs/generate-content/speech-generation)

## 2. Talking video (lip-sync to OUR Bangla audio) → LTX-2 on free Hugging Face GPUs ✅ tested

| Option | Free? | Watermark | Result |
|---|---|---|---|
| **LTX-2 TURBO** Space (`alexnasa/ltx-2-TURBO`): image + audio → video | ZeroGPU quota | none | **Tested: 3 s clip in 40 s, 1024×1536, lips + head + hands move, product held.** Default engine |
| **LTX-2 audio-to-video** Space (`multimodalart/ltx2-audio-to-video`) | ZeroGPU quota | none | Same model family, any length ≤ 12 s. Second engine (API checked, not yet run; quota was spent) |
| Wan2.2-S2V official Space | free (Alibaba's key) | none | **Dead in practice:** queue stuck at 570 jobs |
| Wan2.1 official Space (i2v) | free | optional | **Dead:** accepts jobs, returns nothing |
| LongCat-Video-Avatar 1.5 / OmniAvatar Spaces | ZeroGPU | none | 5 s per run at 2× quota cost: ~1 clip/day. Kept as ideas only |
| Dreamina AI Avatar (OmniHuman) | ~120 credits/day | **yes on free** | Manual fallback |
| Kling AI Avatar | 66 credits/day | **yes on free**, 720p | Manual fallback |
| Google Flow (Veo 3.1 Lite) | 50 credits/day ≈ 5 clips | **yes on free**; makes its own voice, can't take ours | Not used |
| Gemini app video / Grok Imagine / HeyGen / Hedra | paid-only, free tier removed (Grok, Mar 2026), or watermarked | n/a | Not used |
| Local on RTX 3050 | MuseTalk (~4 GB VRAM) fits, but only re-syncs lips on an existing video; full-body models need 16–80 GB | none | Possible future add-on |

ZeroGPU quota ([HF docs](https://huggingface.co/docs/hub/spaces-zerogpu)): **no account 2 min/day, free account 5 min/day**,
"xlarge" Spaces count double, resets 24 h after first use. There is also a run-count limit for anonymous use (hit it today).
Measured today: a 3 s LTX clip used ~71 s of quota; a 5 s clip needs 134 s available. **Free account ≈ 10–20 s of talking video/day.**
Sources: [Dreamina free credits](https://dreamina.capcut.com/ai-video/free-ai-video-generator-usable-clips-guide-2026) ·
[Dreamina pricing (watermark removal is paid)](https://dreamina.capcut.com/pricing/dreamina-price) ·
[Kling pricing](https://www.eesel.ai/blog/kling-ai-pricing) · [Flow credits](https://diyai.io/ai-tools/video-generation/google-veo-pricing/) ·
[Grok free tier ended](https://creatide.ai/blog/grok-imagine-free-tier-ended-why-it-happened-and-what-to-do-next) ·
[Free avatar tools mostly watermark](https://www.flowjam.com/blog/best-free-ai-avatar-tools-2026) ·
[Open-source lip-sync VRAM](https://sync.so/blog/what-is-latentsync) · [Self-hosted avatars](https://www.spheron.network/blog/self-host-ai-avatar-generator-heygen-alternative-2026/)

## 3. Character + product images → free image-edit Spaces ✅ tested

| Option | Free? | Watermark | Result |
|---|---|---|---|
| **FLUX.2-klein-4B** (Apache-2.0), `black-forest-labs/FLUX.2-klein-4B` | ZeroGPU, tiny cost | none | **Tested: 3 scenes, same face, braid, kurta, holding the TONO HIME bottle, with no account** |
| **Qwen-Image-Edit-2511 + Lightning**, `linoyts/Qwen-Image-Edit-2511-Fast` | ZeroGPU, 60 s request | none | Default first engine (multi-image, 4 steps) |
| Qwen-Image-Edit-2511 official Space | asks 360 s per call | none | Too big for free accounts (tested error); PRO only |
| Gemini app (Nano Banana 2) | ~20 images/day | **visible mark** | Manual option |
| Nano Banana via API / AI Studio | no free API tier for any image model | n/a | Not used |
| Qwen Chat web | ~8–10 edits/day reported | reported none | Manual option |
| Pollinations | now "quest/paid pollen" credits | n/a | Not used |
Sources: [Gemini API pricing: image models "Free tier: Not available"](https://ai.google.dev/gemini-api/docs/pricing) ·
[Nano Banana free limits](https://felloai.com/is-nano-banana-free/) · [Pollinations API docs](https://github.com/pollinations/pollinations/blob/main/APIDOCS.md)

## 4. Captions, titles, posters → code, not AI ✅ tested

AI image models still misspell Bangla. So all text is real text:
- Captions: ASS subtitles burned by ffmpeg/libass (HarfBuzz shaping, tested: যুক্তাক্ষর like স্ক, ফ্রে, ত্যি correct).
- Titles, chips, end cards, posters: HTML/CSS rendered by the Edge browser already on Windows (Playwright).
- Fonts (all SIL OFL from Google Fonts): Anek Bangla, Hind Siliguri, Noto Sans/Serif Bengali, Baloo Da 2, Galada,
  Tiro Bangla, Anton, Bebas Neue, Poppins, Montserrat, Playfair Display.
- Product cut-outs: rembg (isnet), with an automatic fade when the product is cropped in the photo.
- Green-screen matting: Robust Video Matting (ONNX, CPU), 15 MB.

## 5. Script writing → Gemini 3.8 Flash (free text tier) ✅ tested

Writes body + 10 hooks (patterns from `02-creative/hook-library.md`) + image prompts + poster copy + ad primary text,
with Meta-policy rules built in. A local word check flags risky claims (নিরাপদ, ১০০%, গ্যারান্টি…),
"you"-style health questions and any price when `show_price: false`.

## 6. Not built (yet): options if you outgrow the free quota

- **Kaggle notebooks:** ~30 free GPU-hours/week (T4/P100) could run LTX-2/InfiniteTalk in batches. Needs a Kaggle
  account + phone verification. [Free GPU overview](https://gpuperhour.com/blog/free-cloud-gpus-and-credits)
- **Local MuseTalk** (~4 GB VRAM, MIT): re-voice one good clip into unlimited hook variants.
- **HF PRO** ($9/mo): 40 GPU-min/day = ~8× more talking video. The only paid item worth considering, and only once
  an angle has proven itself (your principle #4).
