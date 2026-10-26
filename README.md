# Dropshipping Brain

Single source of truth for my dropshipping operation. Everything I've learned, every rule I've paid for, and every asset I reuse lives here.

**Owner:** Xevill (Ashikur Rahman Rifat)
**Started:** 2026-09
**Related workspaces:** `Meta-Ads/` (paid traffic), `Offer-Lab/` (offer + pricing)

---

## Why this folder exists

I've been dropshipping for 2 years. The knowledge is in my head, not on disk. That means:

- I re-solve the same problems every few months
- Claude Code starts from zero every session
- I can't see patterns across products because nothing is logged

This folder fixes all three. It is a **working system, not a course**. Files here are meant to be edited constantly, not read once.

---

## Folder map

```
dropshipping-brain/
├── README.md                       ← you are here
├── CLAUDE.md                       ← instructions for Claude Code in this folder
│
├── 01-playbook/                    ← my rules. Slow-changing. Edit after lessons.
│   ├── principles.md               → hard rules I don't re-litigate
│   ├── product-criteria.md         → my validation checklist + thresholds
│   └── unit-economics.md           → the math that decides kill/scale
│
├── 02-creative/                    ← the current bottleneck. Most active folder.
│   ├── ai-video-stack.md           → which AI tool for which shot, and cost
│   ├── hook-library.md             → swipe file + hook patterns
│   ├── ad-script-templates.md      → DR ad structures with shot lists
│   └── production-workflow.md      → script → generate → assemble → export
│
├── 03-logs/                        ← evidence. Fill these or the brain is useless.
│   ├── product-log.md              → every product tested, and its verdict
│   ├── creative-log.md             → every ad made, its cost, its result
│   └── weekly-review.md            → what I shipped, what I learned
│
└── studio/                         ← ৳0 factory: Bangla UGC videos + posters, one consistent AI character
    ├── README.md                   → how to use it
    └── RESEARCH.md                 → which free tools, why, and their limits
```

---

## Current state

**What I already know (don't need to relearn):**
- Product research and idea generation
- Store setup, social account setup
- Supplier workflow (AutoDS), fulfillment, order handling

**What I'm actively learning:**
- Meta Ads from zero → see `Meta-Ads/` folder
- AI video creation for ad creatives → see `02-creative/`

**The actual bottleneck right now:** creative volume. I cannot test ad angles I cannot produce. Everything in `02-creative/` exists to remove that constraint.

---

## How to use this

**Daily:** work out of `02-creative/`. Log what you produce in `03-logs/creative-log.md`.

**Per product test:** open `01-playbook/product-criteria.md`, score the product, then create its row in `03-logs/product-log.md` before spending a taka.

**Weekly:** fill `03-logs/weekly-review.md`. If a lesson is durable, promote it into `01-playbook/principles.md`.

**Rule:** if I learn something twice, it goes in the playbook. If I learn it three times and it's still not written down, that's the real problem.

---

## Non-negotiables

1. No product goes live without unit economics calculated first.
2. No ad spend without at least 8 creative variants ready.
3. Every kill decision gets logged with the reason. Killed products teach more than winners.
4. Tool subscriptions get reviewed monthly. Unused = cancelled.
