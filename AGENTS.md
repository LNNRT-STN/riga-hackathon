# AGENTS.md

## Mission

Build a proof of concept for a **new way KBC can understand, support, and guide customers at scale**.

KBC provides banking, investment, and insurance services to more than **2.3 million customers**.

The solution must demonstrate how KBC could:

1. Detect what a customer may need.
2. Understand their current situation and intent.
3. Decide what support is relevant.
4. Personalize the experience automatically.
5. Deliver that experience consistently across products and channels.
6. Scale the approach to millions of customers.

This is **not a feature-building challenge**.

Do not optimize for the number of features. Optimize for demonstrating a compelling **personalization system**.
## Current state (KBC Autopilot MVP)

Customers set concrete goals (amount, monthly pace, date); Autopilot suggests goals from their own life signals and their
Payconiq circle, and an LLM spars about realism. It then watches for situations that matter to those goals and shows **one**
card only when it beats doing nothing. The flight metaphor is one hook ("Where do you want to fly to?"), nothing more. It never acts without approval. English only for now.
All data is synthetic and every action is simulated.

The app opens on a **jury tour** (`src/frontend/src/Tour.tsx`, one `STEPS` array): the Bas → Jurre ring story from the deck, then the visitor's own goal, moments that trigger actions, the 2,000-customer engine, and finally the other demo customers.

| Path | What it is |
| --- | --- |
| `src/backend/` | Python **standard library only** (no pip installs). `server.py` (HTTP + API), `engine.py` (features, scoring, rules), `situations.py` (the catalogue: one row per situation), `paths.py` (suggested goals: one row per life event), `ai.py` (Jev + LLM via OpenRouter), `onboarding.py`, `seed.py` (7 demo + 2,000 synthetic customers), `schema.sql`, `test_engine.py`. |
| `src/frontend/` | React + Vite + TypeScript, styled from `DESIGN.md`. Libraries: Radix UI, Lucide icons, sonner. |
| `Dockerfile` | One container for Google Cloud Run (builds the frontend, serves it from the Python server). |
| `PRODUCT.md`, `DESIGN.md` | Product truth and visual system. Read both before UI work. |
| `group/ideation/` | Research and decisions. |

## Run it on a Mac

Requirements: **Python 3.12+** and **Node 20.19+ or 22.12+** (Vite 8). With Homebrew:

```sh
brew install python@3.12 node
git clone https://github.com/LNNRT-STN/riga-hackathon.git && cd riga-hackathon
git switch feat/kbc-autopilot-mvp        # until it is merged into main
```

Build the frontend once, then start the server:

```sh
cd src/frontend && npm ci && npm run build
cd ../backend && python3 server.py        # → http://localhost:8000
```

Frontend development with hot reload (two terminals):

```sh
cd src/backend && python3 server.py       # API on :8000
cd src/frontend && npm run dev            # app on http://localhost:5173, proxies /api to :8000
```

Tests: `cd src/backend && python3 -m unittest` (must stay green).

Notes:
- The database is rebuilt from the seed on every server start (`/tmp/kbc-autopilot.db`); "Reset demo" in the app does the same.
- Port busy? `PORT=8001 python3 server.py` (and change the proxy in `src/frontend/vite.config.ts` for dev).
- Optional container check: `docker build -t kbc-autopilot . && docker run -p 8080:8080 kbc-autopilot`.

## AI keys: never in the repo

The repo is public. There is **no `.env` file**, and none should be added. AI only runs when the key is in your shell:

```sh
export OPENROUTER_API_KEY=...             # current terminal only
python3 server.py
```

The sparring model is `SPAR_MODEL` (default `anthropic/claude-opus-5.5`), card wording `LLM_MODEL`. Without a key, everything works on the offline fallback (keyword checks, templates, rule-based goal extraction).
`python3 seed.py --warm` pre-computes AI answers into `src/backend/ai_cache.json`; that file holds synthetic data only and
may be committed. On Cloud Run the key comes from Secret Manager (see `README.md`).

## Rules for changes

- **New situation = one row in `src/backend/situations.py`.** The engine has no situation-specific code; keep it that way.
- **New suggested goal = one row in `src/backend/paths.py`.** Circle evidence stays aggregated and anonymous.
- Say "goals", "expected date", "on track". The flight metaphor appears once ("Where do you want to fly to?"); the brand word is Autopilot.
- Money maths lives in code, never in the AI. The LLM only rewords a decision and may not change amounts or add urgency.
- Customer value ranks cards; KBC value is logged only. Product cards stay labelled and compared honestly.
- Human in the loop: every money movement goes through the review screen; "Always do this" only between own accounts, capped and revocable.
- No health or diagnosis labels about people (GDPR Art. 9). Credit and investing always hand off to a person.
- UI follows `DESIGN.md`: at most one "For you" card, four bottom tabs, no confetti or animated counters.
- Security counts for 10% of the grade (Aikido): parameterised SQL only, validate every request body, no secrets in git.
- Work on a branch and open a pull request; don't push to `main` directly.
