# Unit Economics

The math that decides kill vs scale. Fill this in **before** launch, every time.

---

## Core formulas

```
Gross margin $     = Sell price − COGS − shipping − payment fees
Gross margin %     = Gross margin $ ÷ Sell price

Break-even ROAS    = 1 ÷ Gross margin %
Break-even CPA     = Gross margin $

Actual ROAS        = Revenue ÷ Ad spend
Contribution/order = Gross margin $ − CPA
```

**Read it this way:** break-even ROAS is the number your ads must beat just to not lose money. Everything above it is profit. Everything below it is tuition.

### Break-even ROAS reference table

| Gross margin % | Break-even ROAS |
|---|---|
| 40% | 2.50 |
| 50% | 2.00 |
| 55% | 1.82 |
| 60% | 1.67 |
| 65% | 1.54 |
| 70% | 1.43 |
| 75% | 1.33 |

Higher margin = lower bar to clear = more room to test creative. This is the entire argument for the 60%+ margin rule.

---

## Per-product worksheet (copy this)

```
Product:
Date:

REVENUE
  Sell price                      $
  Avg order value (with upsells)  $

COSTS PER ORDER
  Product cost (AutoDS)           $
  Shipping to customer            $
  Payment processing (~3%)        $
  Refund/dispute reserve (~3%)    $
  ────────────────────────────────
  Total COGS                      $

MARGINS
  Gross margin $                  $
  Gross margin %                   %

TARGETS
  Break-even ROAS                  x     ← 1 ÷ margin %
  Break-even CPA                  $      ← = gross margin $
  Target ROAS (profit)             x     ← break-even × 1.4 minimum
  Target CPA                      $

KILL THRESHOLD (pre-commit, do not move later)
  Test budget                     $
  Kill if: spend > $____ with < ___ purchases
  Kill if: CPC > $____ after ____ impressions
  Kill if: ROAS < ____ after $____ spend
```

---

## Testing budget rules

Set these once, then follow them.

| Stage | Budget | Decision point |
|---|---|---|
| Creative test | _(e.g. $__/day × 3 days)_ | Which hook gets cheapest CPC / highest hook-rate? |
| Product test | _(e.g. $__ total)_ | Any purchases at all? Any ROAS signal? |
| Scale test | _(e.g. $__/day)_ | Does ROAS hold as spend increases? |

**The rule:** a product doesn't get a second chance on new creative unless it showed *some* signal — a purchase, a strong hook-rate, an add-to-cart pattern. Zero signal at test budget means kill and move on.

---

## Creative cost per test

AI creative isn't free. Track it so I know what a test actually costs me.

```
Monthly tool subscriptions        $
Videos produced per month         #
────────────────────────────────
Cost per video                    $
Videos per product test           #
Creative cost per product test    $
```

**Why this matters:** if a subscription costs $40/mo and I only make 6 videos, each video costs ~$6.70. If I make 60, it costs $0.67. The subscription is only cheap if I actually use it. Review monthly.

---

## My current numbers

_(Fill in and keep updated — this is the section Claude Code should read when I ask "should I kill this?")_

- Typical sell price:
- Typical margin %:
- My break-even ROAS:
- My target ROAS:
- Current test budget per product:
- Current creative cost per video:
