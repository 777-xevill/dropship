# Ad Script Templates

Every script here comes with a **shot list** and which layer of `ai-video-stack.md` generates each shot. Script without a shot list is not a script, it's a wish.

---

## Base structure (20–30s direct response)

```
0–3s    HOOK           Stop the scroll. One idea. See hook-library.md
3–8s    AGITATE        Make the problem specific and felt
8–13s   REVEAL         Product appears as the answer
13–22s  PROOF/DEMO     Show it working. Features as benefits.
22–28s  OFFER + CTA    Price, urgency, what to do next
```

**Non-negotiable:** cut every 1.5–2.5 seconds. AI models hold quality for short clips anyway, so fast cutting is both a creative choice and a technical workaround.

---

## Template A — Problem / Solution

Default for problem-solving products. Highest hit rate for cold traffic.

| Time | Beat | Script slot | Shot | Generate with |
|---|---|---|---|---|
| 0–3s | Hook | "If your [X] keeps [problem]..." | Person reacting, frustrated | Layer 3 (Creatify/Arcads) |
| 3–6s | Agitate | "It's not you. It's [root cause]." | The problem happening, close-up | Layer 2 (Higgsfield) |
| 6–9s | Agitate 2 | "And [worse consequence]." | Consequence visual | Layer 2 |
| 9–13s | Reveal | "This is [product]." | Product hero shot, camera move | Layer 2 (product-in-scene) |
| 13–18s | Demo | "It [mechanism] so you [benefit]." | Product in use | Layer 2 or real footage |
| 18–23s | Proof | "[Number] people already switched." | Reaction / social proof shot | Layer 3 |
| 23–28s | CTA | "Tap the link. [Offer]." | Product + text overlay | Layer 4 (CapCut) |

---

## Template B — UGC Testimonial

Feels like a real person. Best when the product needs explanation or has an objection to overcome.

| Time | Beat | Script slot | Shot | Generate with |
|---|---|---|---|---|
| 0–3s | Hook | "Okay I was wrong about this." | AI actor, casual, mid-thought | Layer 3 |
| 3–7s | Objection | "I thought it was [doubt]." | Same actor, continuous | Layer 3 |
| 7–12s | Turn | "Then I actually tried it." | Cut to product | Layer 2 |
| 12–20s | Result | "Now [specific outcome]." | Demo / result visual | Layer 2 |
| 20–26s | Recommend | "If you [situation], just get it." | Back to actor | Layer 3 |
| 26–30s | CTA | Offer + link | Text overlay | Layer 4 |

**Watch out:** don't let the AI actor hold the product for long. Cut to product-only shots for anything involving hands.

---

## Template C — Demonstration / Satisfying

Zero dialogue. Works for high wow-factor products. Cheapest to produce and travels across languages.

| Time | Beat | Shot | Generate with |
|---|---|---|---|
| 0–3s | Cold open on the satisfying moment | Product doing its thing | Layer 2 |
| 3–8s | Repeat from a second angle | Camera preset variation | Layer 2 |
| 8–14s | Before/after cut | Split or hard cut | Layer 2 + Layer 4 |
| 14–20s | Detail shots, 3 quick cuts | Macro, texture, motion | Layer 2 |
| 20–26s | Result + price reveal | Product + text | Layer 4 |
| 26–30s | CTA | Text overlay + sound sting | Layer 4 |

All text and captions added in CapCut. Generated on-screen text is unreliable.

---

## Template D — Price Shock / Comparison

Best when the product replaces an expensive alternative.

| Time | Beat | Script slot | Shot | Generate with |
|---|---|---|---|---|
| 0–3s | Anchor | "This costs ৳[high]." | Expensive alternative | Layer 2 |
| 3–7s | Pivot | "This does the same for ৳[low]." | Product reveal | Layer 2 |
| 7–15s | Side by side | "Same [outcome]. No [downside]." | Split screen | Layer 4 assembly |
| 15–22s | Demo | Show it performing | Product in use | Layer 2 |
| 22–28s | CTA | Offer + urgency | Text overlay | Layer 4 |

---

## Variant strategy

**The unit of work is not one ad. It is one body with 10 hooks.**

```
1 product
  └─ 1 script body (beats 2–5 stay identical)
       └─ 10 hook variants (0–3s only)
            └─ 8–15 exported files
```

Why: keeping the body constant isolates the hook as the variable. When one wins, I know *why* it won. If I change everything between variants, I learn nothing.

Second round: take the winning hook, vary the **body** while holding the hook constant.

---

## Naming convention

```
[product]_[template]_[hook#]_[version].mp4

lamp_A_h03_v1.mp4
lamp_A_h03_v2.mp4     ← same hook, different cut
lamp_B_h07_v1.mp4
```

Log every export in `03-logs/creative-log.md`. An unnamed, unlogged file is a file I'll regenerate in two months.

---

## Script worksheet (copy this)

```
Product:
Template: A / B / C / D
Hook pattern (from hook-library.md):
Target length:

HOOK (0–3s):
AGITATE:
REVEAL:
DEMO/PROOF:
OFFER + CTA:

SHOT LIST
  1. [___s] shot: ______________  tool: ______
  2. [___s] shot: ______________  tool: ______
  3. [___s] shot: ______________  tool: ______
  4. [___s] shot: ______________  tool: ______
  5. [___s] shot: ______________  tool: ______

Assets needed: (product photos, reference images)
Est. generation cost:
```
