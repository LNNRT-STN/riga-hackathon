# KBC Autopilot

https://kbc-autopilot-1000875003497.us-central1.run.app/

A proof of concept for the KBC hackathon case: **a new way KBC understands, supports and guides 2.3M customers**.

Customers set concrete goals (amount, monthly pace, date). Autopilot suggests goals from their own life signals and their
Payconiq circle, and an LLM helps check whether the goals are realistic. It then watches for situations that matter to those goals and shows
**one** card only when it helps more than doing nothing. It never acts without approval.

**Situations, not segments.** One engine serves every customer. Each situation is one row in
[`src/backend/situations.py`](src/backend/situations.py) and is scored as
`customer value × goal weight × confidence − annoyance`, compared with doing nothing. Customer value ranks cards;
KBC value is only logged. The app opens on a short jury tour, then lets you switch between demo customers.

## Run it

Requirements: Python 3.12+ and Node 20.19+ or 22.12+.

```sh
cd src/frontend && npm ci && npm run build
cd ../backend && python3 server.py        # → http://localhost:8000
python3 -m unittest                       # tests
```

AI is optional. Set `OPENROUTER_API_KEY` in your shell (never in a file, since the repo is public). Without it, every flow
falls back to keyword checks, templates and rule-based goal extraction.

Deploy: `gcloud run deploy kbc-autopilot --source . --set-secrets OPENROUTER_API_KEY=openrouter-key:latest`
(one instance, so all visitors share one demo state).

## Unfinished

- **Everything is simulated.** Customers are synthetic (7 demo + 2,000 generated), and no real money, forms or advisor calls are involved.
- **English only.** Dutch and French are not done yet.
- **Six situations** are wired end to end. More are one catalogue row each but not written yet.
- **Circle signals** would need peer consent and a k-anonymity floor (≥ 5 people) before a real pilot.
- **No real login or KBC integration.** The database is rebuilt from the seed on every start, and "Reset demo" does the same.
- **Credit and investing** only hand off to a person. Autopilot gives no advice on them.

More detail: [`AGENTS.md`](AGENTS.md) (setup, rules), [`PRODUCT.md`](PRODUCT.md), [`DESIGN.md`](DESIGN.md).
