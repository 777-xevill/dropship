# Studio: free Bangla UGC videos + posters, one consistent character

Built 2026-10-15. Cost: **৳0**. Everything runs on free tiers plus this PC.
Research and tool choices (with sources): [RESEARCH.md](RESEARCH.md).

## What it makes

| Output | Looks like | Needs GPU quota? |
|---|---|---|
| **selfie** video | your `ugc2.mp4`: character holds the product and talks to the camera, jump cuts, product cut-ins, captions | yes (talking clips) |
| **greenscreen** video | your `ugc1.mp4`: full-screen product b-roll, character cut out bottom-right, title on top | yes (more: she talks the whole time) |
| **faceless** video | product b-roll + her voice + captions | **no**: unlimited |
| **posters** (6 templates) | your `poster-page/` refs: split, feature cards, giant word, person hero, text-behind-subject, offer | no (the person hero needs 1 image) |

Every video: Bangla voice in **the same designed voice**, Bangla captions with the spoken word highlighted,
hook title, ✓ chips, branded end card with your phone number, music ducking (if you add music), 1080×1920.
**One hook = one variant**: 10 hooks → 10 files, same body. That's your 8–15 variant rule.

## How consistency is kept

| Thing | How |
|---|---|
| Face/body | Every image is made *from her reference photo* (image 1) + your product photo (image 2). Never from words. |
| Video | Talking clips start from those images, so the face carries through. |
| Voice | A custom Gemini voice designed once for her (`voice.id` in `character.yaml`), same style text every time. |
| Look | Same outfit text, same caption/title style, colours taken from each product. |

---

## One-time setup (10 minutes)

1. **Check:** open PowerShell and run
   ```
   E:\Dropship\studio\studio.bat doctor --test
   ```
   Everything should say `[ok]`. (Gemini key is already in `studio\.env`, copied from `E:\Millionear\.env`.)

2. **Free Hugging Face token (strongly recommended).** Without it you get 2 GPU-minutes a day; with it you get 5.
   - Sign up at huggingface.co (free, no card) → Settings → Access Tokens → *Create new token* → type **Read**.
   - Paste it in `E:\Dropship\studio\.env` after `HF_TOKEN=`.

3. **Optional music:** drop royalty-free `.mp3` files into `studio\assets\music\`
   (Meta Sound Collection inside Meta Business Suite is safest for FB/IG ads; YouTube Audio Library or Pixabay Music also work).
   No music = voice only, which is fine for UGC.

Tip: add `E:\Dropship\studio` to your Windows PATH and you can type just `studio ...` anywhere.

## Add YOUR character (once)

Use 1–3 clear photos of the same person: face clearly visible, waist-up, natural light, simple clothes.
```
studio character nila --image "D:\pics\nila_front.png" "D:\pics\nila_side.png" --display নীলা
```
This copies the photos to `characters\nila\ref\`, has Gemini describe her (`character.yaml`) and **designs her own Bangla voice**.
Listen to `characters\nila\voice_sample.wav`. Don't like it? Run the command again, or put a prebuilt voice
name in `voice.name` (Sulafat, Leda, Aoede = female; Achird, Orus, Charon = male) and delete `voice.id`.

There is already a test character **`demo`** (মিতু, from the stills of the last session). Delete
`characters\demo` when you have your own.

## Every product

```
studio product perfume01 --photos "D:\p\front.jpg" "D:\p\box.jpg" --name "Rose Oud Perfume" --page "Your Page" --phone 017XXXXXXXX --character nila
```
Then open `products\perfume01\project.yaml` and fill `product:` in plain words (Bangla or English):
`what_it_is`, `benefits`, `proof` (only true things), `avoid` (claims you must not make).
No price in ads? Leave out `--price`: `show_price: false` keeps money out of every line.

```
studio write perfume01      ← Gemini writes the Bangla script + 10 hooks + image prompts + poster copy
```
Read `project.yaml` and fix any wording; it's yours to edit. Every run checks for risky ad words (Meta policy).

```
studio make perfume01       ← voice → character images → talking clips → videos → posters
```
**Run `studio make perfume01` again the next day**: it continues where the free GPU quota stopped.
Nothing is made twice.

```
studio status perfume01     ← what's done / waiting
studio log perfume01        ← adds the finished files to 03-logs\creative-log.md
```
Finished files: `products\perfume01\final\{selfie,greenscreen,faceless}\` and `products\perfume01\posters\`.
Names follow your convention: `perfume01_B_h03_v1.mp4` (B = selfie, G = green-screen, C = faceless).

### Realistic daily output (free)

| Step | Free limit | What it means |
|---|---|---|
| Voice (Gemini 3.8 TTS) | 10 requests/day per model | the studio batches lines: **~2 requests per product** |
| Character images | HF GPU quota | ~3–4 images per product, usually all on day 1 |
| Talking clips (LTX-2) | 5 GPU-min/day with token | **~10–20 s of talking video per day** |
| Faceless videos, posters, captions, editing | none | unlimited, on this PC |

So a typical product: **day 1** script + voice + images + faceless variants + posters; **day 2–3** the selfie
body + first hooks; **day 3–4** the green-screen version. Talking clips are made body-first, so the part
shared by every variant is finished first.

## Choosing what to make

```
studio make perfume01 --formats selfie,faceless      ← skip green-screen (saves half the GPU time)
studio build perfume01 --hooks h01,h04,h07           ← only some variants
studio posters perfume01 --sizes 4:5,1:1,9:16        ← feed, square and story sizes
studio build perfume01 --allow-missing               ← build now; missing talking clips become product shots
studio make perfume01 --redo-voice                   ← record all lines again (after a backup voice was used)
```

In `project.yaml`, each line has a `visual:`
- `talk`: the character on camera (selfie/green-screen)
- `product`: your product cut-out on a branded stage (pop-in, float, light sweep)
- `photo:photos/texture.jpg`: one of your real photos as a moving card (great for demos and texture)
- `scene:use_1`: an AI image you add under `scenes:` (e.g. `use_1: the person from image 1 applying ...`)

Other switches: `voice_speed: 1.08` (1.0 = as recorded), `caption_style: pop | clean | box`, `title_style: white | brand | yellow`, `music: none`, `sfx: false`.

## When a free tool is down or quota is gone: do it by hand (still free)

The studio writes **`products\<slug>\inbox\TODO.md`** with the exact prompt and the files to upload.
- **Images:** Qwen Chat (chat.qwen.ai), Gemini app, or Copilot → save as `inbox\scene_selfie_a.png` etc.
  (Gemini app images carry a small visible watermark; Qwen Chat and the HF engines don't.)
- **Talking clips:** Dreamina AI Avatar, Kling Avatar or HeyGen photo avatar with the exported `.png` + `.wav`
  → save as `inbox\talk_selfie-b01.mp4` etc. **Free tiers of these add a watermark**, which is why the studio's own
  engine (LTX-2 on Hugging Face) is the default.
Run the command again: inbox files are picked up automatically.

## Honest limits

- **Labels and hands:** AI redraws small label text and fingers. Real product photos appear in the cut-ins
  and end card, so the true label is always shown. Use clean, full product photos (whole product in frame, plain background).
- **Talking time is the bottleneck:** ~10–20 s/day free. Faceless + posters are unlimited, so test those angles while clips render.
- **Free services change:** model names and Spaces can move. Engines and models are settings in `studio\.env`
  (see `config.py`); the fallbacks kick in automatically, and `RESEARCH.md` lists alternatives.
- **Honesty rule:** scripts default to `script_style: explainer`. She explains and recommends; she never claims
  she personally used the product (an AI person can't). That keeps you inside Meta's rules and your own brand promise.

## Troubleshooting

| Message | Fix |
|---|---|
| `Free GPU quota for today is used up ... Try again in HH:MM` | Wait, or add `HF_TOKEN`. Everything made so far is kept. |
| `free daily limit reached on gemini-3.8-flash-tts` | Backup voice used today. Tomorrow: `studio make <slug> --redo-voice`. |
| `Space ... is waking up or rebuilding` | Try again in 5–10 min. |
| `scene ... waiting for you -> see inbox/TODO.md` | Make that image by hand (above), or rerun tomorrow. |
| A video looks wrong | Delete the file in `final\` and the product's `work\segments\`, then `studio build <slug>`. |

## Files

```
studio\
  studio.bat               the command
  .env                     GEMINI_API_KEY, HF_TOKEN
  characters\<name>\       character.yaml, ref\ photos, voice_sample.wav
  products\<slug>\         project.yaml, photos\, inbox\, final\, posters\, work\ (cache, safe to delete)
  templates\posters\       6 poster designs (HTML/CSS: edit colours, fonts, layout)
  templates\overlays\      hook title, chips, end card, product stage
  assets\fonts\            Bangla + Latin fonts (all SIL Open Font License)
  assets\music\            your music
  studio\                  the Python code
```
