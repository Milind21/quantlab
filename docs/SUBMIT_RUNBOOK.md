# Capstone submission runbook — Vibecoding Agents Capstone Project

**Deadline: 2026-07-07 06:59 UTC. One submission per team.** Track: **Agents for Business**.

## What a valid submission needs (all required)
1. **Kaggle Writeup** (≤2500 words, title + subtitle, a Track selected) — source: [`WRITEUP.md`](../WRITEUP.md)
2. **Media Gallery** with a **cover image** (required)
3. **Video** (≤5 min, on YouTube) — script: [`VIDEO_GUIDE.md`](VIDEO_GUIDE.md)
4. **Public project link** — a public GitHub repo with README + setup (we have it)

## Step 1 — Publish the public GitHub repo (needs you)
The public link must be a standalone public repo (not the private `kaggle_projects` monorepo).
From `5dgai_capstone/` (it's already self-contained: src/ tests/ configs/ Dockerfile LICENSE
README.md WRITEUP.md INTELLIGENCE.md docs/):

```bash
# create an EMPTY public repo on github.com named e.g. "quantlab" (no README/license), then:
cd /Users/milind/Desktop/kaggle_projects/5dgai_capstone
git init -b main
git add -A                     # .gitignore already excludes .venv/ data/ runs/ .env / active.yaml
git commit -m "QuantLab — guardrailed multi-agent market-intelligence layer (capstone)"
git remote add origin git@github.com:<you>/quantlab.git
git push -u origin main
```
Sanity-check before pushing: **no `.env`, no `data/`, no `runs/`, no API keys** (`git status` +
`grep -ri "AIza\|api_key" src` should be clean). The `.gitignore` already handles this.

## Step 2 — Record + upload the video
Follow `VIDEO_GUIDE.md`. Clean state first (`rm -f runs/intel.db && rm -rf runs/intel runs/proposals
configs/active.yaml`). Upload to YouTube (public/unlisted), grab the URL.

## Step 3 — Cover image
The README architecture diagram on a clean background + title. Any tool (Excalidraw/Canva/screenshot).

## Step 4 — Submit on Kaggle
1. **Join** the competition (accept rules) if not already: https://www.kaggle.com/competitions/vibecoding-agents-capstone-project
2. Click **New Writeup** → paste `WRITEUP.md`, set title/subtitle, **select Track = Agents for Business**.
3. **Media Gallery**: attach the cover image + the YouTube video.
4. **Project link**: the public GitHub repo URL from Step 1.
5. Click **Submit** (top-right). Confirm it shows as submitted (draft writeups are NOT judged).

## Pre-submit checklist
- [ ] Writeup ≤2500 words, Track = Agents for Business, cover image + video attached, repo link set
- [ ] Video ≤5 min, public on YouTube, shows: problem → why agents → architecture → **live demo
      (SUSPECT flag + injection→no-proposal + approve/rollback)** → the build
- [ ] Public repo: README renders, `LICENSE` = CC-BY-4.0, no secrets, quickstart runs
- [ ] ≥3 course concepts visible (we have 4: multi-agent, security, MCP, CLI)
- [ ] Clicked **Submit** before 2026-07-07 06:59 UTC
