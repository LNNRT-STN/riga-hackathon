# KBC Autopilot

A proof of concept for the KBC hackathon case: **a new way KBC understands, supports and guides 2.3M customers**.

> You tell Autopilot where you want to fly to. It watches for situations that matter to your goals, shows **one** card only
> when it clearly helps, stays quiet otherwise, and never acts without your approval.

**Situations, not segments.** Every customer goes through one engine. Each situation (cash shortage ahead, bill went up,
sports club refund, trouble logging in, room to top up a goal, deposit matures) is one row in
[`src/backend/situations.py`](src/backend/situations.py). A card is shown only when
`customer € × goal weight × confidence − annoyance` beats doing nothing. Customer value ranks cards; KBC value is only logged.

All customer data is synthetic. Every transfer, form and advisor call is simulated.

## Run locally

```sh
cd src/frontend && npm ci && npm run build      # React + Vite
cd ../backend && python3 server.py              # Python standard library only → http://localhost:8000
python3 -m unittest                             # engine, safety and onboarding checks
```

For frontend work, run `python3 server.py` and `npm run dev` side by side (Vite proxies `/api`).

### AI (optional)

Jev (typed yes/no screening) and the LLM (card wording, onboarding) run through OpenRouter **only** when
`OPENROUTER_API_KEY` is set in the environment. There is no `.env` file in this public repo. Without a key, every flow
uses the offline fallback (keyword checks, templates, rule-based goal extraction), so the demo always works.

```sh
export OPENROUTER_API_KEY=...        # in your shell only, never in a file
python3 seed.py --warm               # optional: pre-compute AI answers into ai_cache.json (synthetic data, safe to commit)
```

## Deploy (Google Cloud Run)

```sh
PROJECT=<your-project-id>; REGION=us-central1
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
printf %s "$OPENROUTER_API_KEY" | gcloud secrets create openrouter-key --data-file=-     # optional
gcloud run deploy kbc-autopilot --source . --region $REGION --allow-unauthenticated \
  --min-instances 1 --max-instances 1 \
  --set-secrets OPENROUTER_API_KEY=openrouter-key:latest    # omit this line to run offline
```

One instance keeps one shared demo state; the database is rebuilt from the seed on every start, and **Reset demo** restores
it. Put a spend cap on the OpenRouter key: the URL is public. The live AI endpoints are rate-limited per visitor.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/backend/` | Engine (`engine.py`), catalogue (`situations.py`), AI calls (`ai.py`), onboarding, server, seed, tests. |
| `src/frontend/` | React app styled from `DESIGN.md` (Radix primitives, Lucide icons, sonner toasts). |
| `group/ideation/` | Research and decisions, e.g. [`2026-09-30-research.md`](group/ideation/2026-09-30-research.md). |
| `PRODUCT.md`, `DESIGN.md` | Product truth and the KBC-inspired visual system. |
| `AGENTS.md` | Contributor and agent workflow. |
