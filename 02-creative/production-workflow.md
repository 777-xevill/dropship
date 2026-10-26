# Production Workflow

Script → generate → assemble → export. Repeatable, so creative volume stops being the bottleneck.

**Target throughput:** 10–15 ad variants per product test, in one working day.

---

## The pipeline

### Stage 0 — Prep (once per product)
- [ ] Product scored in `01-playbook/product-criteria.md`
- [ ] Unit economics done, break-even ROAS known
- [ ] Collect **8–12 clean product photos**: front, angles, in-use, detail, scale reference
- [ ] Pick 1 photo as the **locked reference image** for consistency across shots
- [ ] Write the offer (from `Offer-Lab/`)

### Stage 1 — Script (30–45 min)
- [ ] Pick a template from `ad-script-templates.md`
- [ ] Write **one body**
- [ ] Write **10 hooks**, each from a *different* pattern in `hook-library.md`
- [ ] Build the shot list, mark which tool generates each shot

### Stage 2 — Generate (2–3 hours)
Generate **body shots once**, hooks separately. Body is reused across all 10 variants — this is where the time savings live.

- [ ] Body shots (Layer 2 for product, Layer 3 for actor)
- [ ] 10 hook clips
- [ ] Generate 2–3 takes of any shot that matters. First output is rarely the best.
- [ ] Dump everything into `/raw/` with the naming convention

**Prompting notes for product shots:**
- Feed the locked reference image every time
- Specify camera move explicitly (push in, orbit, crash zoom, static)
- Specify lighting and surface ("soft studio light, matte white surface")
- Keep clips 3–5s. Longer = more artifacts.
- Never ask the model to render on-screen text

### Stage 3 — Assemble (1–2 hours)
In CapCut:
- [ ] Build the master timeline: body only, no hook
- [ ] Cut every 1.5–2.5s
- [ ] Add sound: one trending or driving track + sound effects on cuts
- [ ] Add all text overlays (never generated text)
- [ ] Duplicate the master 10×, drop a different hook on the front of each

### Stage 4 — Polish (30 min)
- [ ] Captions through Submagic (or CapCut auto-captions if not subscribed)
- [ ] Check on a phone at arm's length. If the hook doesn't land muted, it fails.
- [ ] Check 9:16 safe zones — nothing important under the CTA bar

### Stage 5 — Export and log
- [ ] Export 9:16, 1080×1920, .mp4
- [ ] Name using the convention in `ad-script-templates.md`
- [ ] Log every file in `03-logs/creative-log.md` with tool used and generation cost
- [ ] Hand off to `Meta-Ads/` folder for campaign setup

---

## Folder structure per product

```
products/[product-name]/
├── script.md              ← body + 10 hooks + shot list
├── assets/                ← product photos, reference image
├── raw/                   ← every generated clip, including rejects
├── final/                 ← exported variants ready to upload
└── results.md             ← performance pulled back from Meta Ads
```

Keep the rejects. Knowing what a tool fails at is worth as much as knowing what it does well.

---

## Quality gate

Before an ad goes live, all four must be true:

1. **Muted test** — hook lands with sound off
2. **Thumb test** — I'd stop scrolling on my own phone
3. **Claim test** — nothing said that Meta ad policy would flag, and nothing I can't back up
4. **Product test** — the product is clearly visible and understandable within 10 seconds

Fail any one, fix before spending.

---

## Time budget

| Stage | Target |
|---|---|
| Prep | 30 min |
| Script | 45 min |
| Generate | 2–3 hr |
| Assemble | 1–2 hr |
| Polish | 30 min |
| **Total per product (10–15 variants)** | **~6 hr** |

If it takes longer than this, the bottleneck is a specific stage. Log which one and fix that stage, not the whole process.

---

## Bottleneck log

| Date | Product | Stage that ate the time | Fix applied |
|---|---|---|---|
| | | | |
| | | | |
