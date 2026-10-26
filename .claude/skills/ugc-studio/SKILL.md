---
name: ugc-studio
description: Make Bangla UGC ad videos (selfie / green-screen / faceless) and product posters with the user's consistent AI character, for free, using the studio in E:\Dropship\studio. Use when the user asks to make, script, render, continue or fix a video, hook variants, voice-over or poster for a product, or to add/change their character.
---

# UGC Studio (E:\Dropship\studio)

Read `E:\Dropship\studio\README.md` once per session if you need detail. Research/tool choices: `RESEARCH.md`.

## Run commands
Use the PowerShell tool (quoting is reliable there):
```
& "E:\Dropship\studio\studio.bat" <command> [args]
```
Commands: `doctor [--test]`, `character <name> --image <files> [--display <bn name>]`,
`product <slug> --photos <files> --name ".." --page ".." --phone ".." --character <name> [--price ".."]`,
`write <slug> [--force]`, `make <slug> [--formats selfie,greenscreen,faceless] [--hooks h01,h02] [--redo-voice]`,
`voice|scenes|talk|build|posters <slug>`, `status <slug>`, `log <slug>`.

## Workflow for "make a video/ad for <product>"
1. `status <slug>`. If the product doesn't exist: create it, then fill `products/<slug>/project.yaml` → `product:`
   (what_it_is, benefits, proof, avoid) from what the user told you and their strategy files. Ask only for facts you can't find.
2. `write <slug>`, then **read the script yourself**: natural spoken Dhaka Bangla, ≤ 11 words per line,
   no fake personal experience (explainer style), no banned claims, and no price if `show_price: false`.
   Edit `project.yaml` directly to fix lines. You may rewrite hooks in better Bangla; keep `id`s.
3. `make <slug>`. Read the Summary: quota messages are normal. Tell the user what was made, what's pending and
   when to rerun (free GPU quota resets 24 h after first use; voice quota resets daily).
4. Show results: extract a few frames with ffmpeg and look at them before claiming quality.
5. Remind the user to log (`log <slug>` appends DRAFT rows to `03-logs/creative-log.md`).

## Rules
- Private Choice BD / TONO HIME: never any price anywhere; CTA = call 01612-237962 (see memory).
- Health/intimate products: comfort/health framing only, no sexual words, no "you"-questions about the body.
- Don't invent performance numbers. Vendor claims are labelled vendor-reported.
- Free-tier watermarks: never add watermark-removal steps. The default engines (HF Spaces) don't add any.
- Character consistency comes from reference images: scene prompts must say "the person from image 1"
  and "the product from image 2", not describe the face.

## Where things are
- Characters: `studio/characters/<name>/character.yaml` (+ `ref/`, `voice_sample.wav`). `demo` is a test character.
- Products: `studio/products/<slug>/` → `project.yaml`, `photos/`, `inbox/` (manual drops + TODO.md), `final/`, `posters/`.
- Engines/models are env-configurable in `studio/studio/config.py` (`STUDIO_SPACE_TALK`, `STUDIO_TTS_MODELS`, ...).
