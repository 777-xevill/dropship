# AI Video Stack

**Last verified:** 2026-09-09 — this file goes stale fast. Re-check tools and prices quarterly.

> **2026-10-15: the ৳0 route is built and is the default now** → `studio/` (guide: `studio/README.md`,
> evidence: `studio/RESEARCH.md`). Gemini TTS (free, Bangla, designed voice) + LTX-2 lip-sync and FLUX.2-klein /
> Qwen-Image-Edit on free Hugging Face GPUs + local captions/posters. No subscriptions, no watermarks.
> **Flagged as outdated below:** the paid tools and prices were not re-verified; Kling and Dreamina free tiers
> watermark, Grok Imagine's free tier ended (Mar 2026), Gemini app video is paid-only. Re-check before paying for anything.

The mistake is asking "which tool makes the video." There is no single tool. There are four layers, and the skill is knowing which layer a given shot needs.

---

## The four layers

### Layer 1 — Base models
Raw clip generation from text or image. Current generation: **Veo 3.1, Sora 2, Kling 3.0, Seedance 2.0, Runway Gen-4.5**.

I mostly don't touch these directly. Aggregator platforms bundle them, which is cheaper than subscribing to each. Direct access only makes sense if one specific model is doing all my work.

### Layer 2 — Product-in-scene / cinematic control
**Higgsfield, PixVerse.**

Takes my actual product photo and puts it in a generated scene with controlled camera motion, keeping the product consistent across frames. General video models are bad at product consistency — this is the specific problem this layer solves.

- **Higgsfield** — camera-control presets (bullet time, crash zoom, 360 rotation), multi-model access in one workspace, and a Marketing Studio that takes a product URL, scrapes the details, writes a brief, and outputs a draft ad. Strongest at product-placement and cinematic motion. Weakest as a general video editor.
- **PixVerse** — Ad Master workflow turns one product photo plus selling points into a short commercial-style spot. Lighter and faster than Higgsfield for single-photo motion.

### Layer 3 — AI UGC actors
**Creatify, Arcads.** The workhorse for direct-response dropshipping.

A synthetic person talks about or holds the product. This is what most performing dropshipping ads actually look like.

- **Creatify** — URL-to-ad pipeline. Paste a product link, it pulls assets, writes a script, generates a creator-style vertical video. It genuinely renders the physical product in frame, and it publishes pricing. Better fit for physical products.
- **Arcads** — larger, more natural-feeling actor library, strongest on delivery realism for testimonial-style ads. Pricing is gated behind signup. Better when the creative is a person talking, weaker on product handling.

Neither fully solves an avatar realistically handling a physical object. Expect to cut around that limitation.

### Layer 4 — Assembly and post
**CapCut, Submagic.**

Hook stitching, captions, pacing, sound design, aspect ratios. Submagic's real job is caption styling — run Layer 2/3 output through it before publishing.

**This is where most of the ad performance actually lives.** Layers 1–3 give me footage. Layer 4 turns footage into an ad.

---

## Decision tree

```
What kind of shot do I need?

├─ A person talking about the product
│  ├─ Product must be visible in their hands  → Creatify
│  └─ Pure talking-head testimonial           → Arcads (if budget) / Creatify
│
├─ The product itself, no person
│  ├─ From my real product photos             → Higgsfield product-in-scene / PixVerse
│  ├─ Cinematic B-roll, dramatic motion       → Higgsfield (camera presets)
│  └─ Quick zoom/pan from one photo           → PixVerse Ad Master
│
├─ Fast draft of a whole ad from a link       → Higgsfield Marketing Studio / Creatify URL-to-video
│
└─ Assembly, captions, hooks, export          → CapCut + Submagic  (always)
```

---

## Cost reality

| Tool | Layer | Rough price | Notes |
|---|---|---|---|
| CapCut | 4 | Free | Non-negotiable base |
| Meta Ad Library | — | Free | Research, not production |
| TikTok Creative Center | — | Free | Research |
| Higgsfield Pro | 2 | ~$17/mo | Entry tier, decent credits |
| Higgsfield Plus | 2 | ~$39/mo | Full model access |
| Creatify | 3 | ~$29–33/mo | Public pricing |
| PixVerse | 2 | varies | Cheaper single-photo workflow |
| Arcads | 3 | ~$100/mo | Signup-gated pricing |
| Submagic | 4 | varies | Caption polish |

**Prices as of Sept 2026 — verify before subscribing.**

### My subscription rule

**One paid subscription at a time until I've shipped 20 ads.** Free tier + CapCut + Ad Library first. Add a paid tool only when a specific shot type is blocking me, and cancel it if the cost-per-video in `01-playbook/unit-economics.md` goes above what a test can absorb.

Current subscriptions:
- [ ] _(none yet)_

---

## What I'm NOT buying

- All-in-one "AI ad agents" that promise to generate *and* launch campaigns. I'm learning Meta Ads myself in the `Meta-Ads/` folder. Outsourcing the buying to a black box before I understand it means I learn nothing.
- Multiple overlapping subscriptions in the same layer.
- Anything whose main pitch is a self-reported ROAS number.

---

## Honest limitations

Things AI video still does badly. Design creatives around these, don't fight them:

- **Hands holding products.** Warping, extra fingers, product morphing between frames. Cut away or use a real product photo insert.
- **Text on screen.** Generated text is unreliable. Add all text in CapCut.
- **Long shots.** Most models hold quality for a few seconds. Build ads from many short cuts, which suits short-form pacing anyway.
- **Emotional range.** AI actors read scripts; they don't feel them. Fine for hooks and feature callouts, weaker for genuine testimonial emotion.
- **Consistency across clips.** Same "person" or same product across shots drifts. Lock a reference image and keep shots short.

---

## Update log

| Date | What changed | Action taken |
|---|---|---|
| 2026-09-09 | File created | Baseline stack documented |
| 2026-10-15 | Checked free route: Gemini free tier makes images but **video (Veo) needs a paid plan**. Free Bangla female voice works via `edge-tts` (bn-BD-NabanitaNeural). | Built a ৳0 UGC-style ad from 4 Gemini stills + edge-tts voice + ffmpeg (`my-product/creatives/src/ugc/`) |
| 2026-10-15 | Deep check of free tools. Gemini 3.8 Flash TTS: free, natural Bangla, custom voice design, 10 req/day/model. LTX-2 on free HF ZeroGPU does image+audio→lip-synced video (tested). FLUX.2-klein keeps the character's face across scenes (tested). Free avatar tiers (Dreamina, Kling, HeyGen, Hedra) watermark. | Built `studio/`: reusable pipeline for selfie / green-screen / faceless videos + 6 poster templates. |
| | | |
