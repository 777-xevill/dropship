# Instructions for Claude Code in this folder

## Context you should load

Before answering anything substantive, read:
- `README.md` — what this folder is and current state
- `01-playbook/principles.md` — my standing rules
- Whichever `02-creative/` file matches the task

Don't read the whole tree every time. Read what the task needs.

## Who I am

Solo operator in Dhaka, Bangladesh. 2 years of dropshipping experience. I already know product research, store setup, social accounts, and supplier workflow (AutoDS). **Do not explain these to me.**

My real gaps:
- Meta Ads (learning from zero, separate folder)
- AI video creation for ad creatives (learning now, `02-creative/`)

## How to talk to me

- Direct and action-oriented. Lead with the answer.
- No motivational preamble. No "great question."
- If I'm wrong, say so plainly and say why.
- English or Banglish both fine.
- Assume competence on ecommerce fundamentals, assume beginner on paid ads and AI video.

## Standing rules for this folder

1. **Never invent performance numbers.** If a claim about CTR, ROAS, or CPA came from a tool vendor's marketing, label it as vendor-reported. My own numbers come from `03-logs/`.

2. **Cost matters.** I'm a solo operator, not an agency. Before recommending a tool, check what's already in `02-creative/ai-video-stack.md` and whether I already pay for something that does the job.

3. **Log discipline.** If a session produces a creative or a product decision, remind me to log it. An unlogged test is a wasted test.

4. **Don't recommend a "perfect" ad.** The unit of work is 8–15 variants of the same product with different hooks. Optimize for volume and iteration speed, not polish.

5. **Prices and tools go stale fast.** AI video tooling changes every few months. If I ask about a tool, check the current state rather than answering from memory, and flag anything in `ai-video-stack.md` that looks outdated.

## Common tasks

| I say | You should |
|---|---|
| "Write hooks for [product]" | Pull patterns from `02-creative/hook-library.md`, write 10, vary the pattern not the wording |
| "Script this ad" | Use a structure from `ad-script-templates.md`, output with shot list + which tool generates each shot |
| "Should I kill this product?" | Ask for the numbers, run them against `01-playbook/unit-economics.md`, give a straight verdict |
| "Score this product" | Use `01-playbook/product-criteria.md`, give a number and the weak axis |
| "Log this" | Append the row to the right file in `03-logs/` in the existing table format |
| "Make a video / poster for [product]" | Use the free studio in `studio/` (skill `ugc-studio`, guide `studio/README.md`) |
