# Flight paths: suggestions, concrete goals, sparring. API contract

Shared contract between backend (`src/backend`) and frontend (`src/frontend`). Keep both sides to this shape.

## Concepts

- A **flight path** is one goal row (`goal` table). A customer has up to 5.
- A **suggested flight path** is a goal Autopilot proposes from the customer's own life signals (payments) and from their
  **Payconiq circle** (people they pay with Payconiq who set a similar goal). Suggestions are never saved until the customer
  adds them. Circle evidence is aggregated and anonymous: never a friend's name.
- A goal may carry a **customer-chosen monthly amount** (`monthly_eur`). If 0 or absent, the engine splits the usual
  monthly room (`pace_for`).

## Schema

- `txn.peer_id INTEGER NULL`: the other customer in a Payconiq payment (both directions). NULL for shops and salary.

## New module `src/backend/paths.py`

`PATHS`: one row per life event (like `situations.py`; the engine has no event-specific code):

```py
Path(key, title, type, horizon, target_eur, months, own=(keywords in counterparty/description, lower-case),
     peer=(keywords in a circle goal title, lower-case) | (), reason="plain-language reason")
```

Rows: baby (PRENATAL, DREAMBABY, KRUIDVAT BABY, LUIERS, PAMPERS -> "Studies for your child", save_for, 25 000, 18 years),
wedding (BLOEMEN, FLEURS, FLOWER, JUWELIER, JEWEL -> "Wedding ring", save_for, 3 000, 12 months, peer=("ring", "wedding")),
travel (RYANAIR, BRUSSELS AIRLINES, BOOKING.COM -> "Next trip", save_for, 1 500, 6 months, peer=("trip", "holiday", "travel")),
car (D'IETEREN, VAB, CARGLASS -> "Next car", save_for, 12 000, 36 months, peer=("car",)),
pet (ZOOPLUS, DIERENARTS, TOM&CO -> "Vet buffer", buffer, 800, 12 months),
home (IMMOWEB, NOTARIS -> "Own home", save_for, 40 000, 72 months, peer=("home", "house", "flat")).

`suggest(txns, peer_goals, goals, today=TODAY) -> list[dict]`, max 3, ranked by score (own hit = 1, circle hit = 1; both = 2):

```py
{"key": "baby", "title": "Studies for your child", "type": "save_for", "horizon": "long", "target_eur": 25000.0,
 "deadline": "2044-09-30", "reason": "...", "evidence": ["Payments to DREAMBABY, KRUIDVAT BABY", "2 people in your Payconiq circle set a similar goal"],
 "source": "life" | "circle" | "both"}
```

- `peer_goals` = `[{"title", "type"}]` of customers linked via `txn.peer_id` in the last 90 days, only peers with `consent_help = 1`.
- A path is skipped when the customer already has a goal with the same title (case-insensitive) or, for `buffer`, any buffer goal.
- Circle-only suggestions (no own signal) are allowed but rank below life+circle. `ponytail:` note the k-anonymity threshold for a real pilot.

## Customer view additions (`GET /api/customers/{id}` and every response that returns a view)

- `suggestions: Suggestion[]` (shape above), for every customer, onboarded or not.
- `goals[]` gains `priority: number`.

## Goals

- `POST /api/customers/{id}/goals` body `{ goals: DraftGoal[] }`: unchanged, but each goal may carry `monthly_eur` (0..100000).
  `monthly_eur > 0` is the customer's own pace; else the engine's share. `saved_eur` is carried over for goals whose title
  matches an existing goal (so editing the plan does not wipe progress).
- `POST /api/customers/{id}/add-goal` body `{ goal: DraftGoal }` -> `Customer`. Appends one goal (next priority),
  leaves the others and their rules untouched. 400 if it would be the 6th goal or the title already exists.

## Onboarding

- `POST /api/customers/{id}/onboarding` body `{ history, goals?: DraftGoal[] }`. `goals` is the customer's current draft
  (after manual edits); the model gets it as "current draft" and must keep it unless the customer changes it.
- The reply shape is unchanged: `{ reply, goals, turns_left, source }`. `goals[]` keep `monthly_eur` (customer's own if set).
- The sparring model is `SPAR_MODEL` (env, default `anthropic/claude-opus-5.5`, OpenRouter id); card wording stays on `LLM_MODEL`.
- `summary(cid)` (what the guide may know) gains `suggestions: [{title, target_eur, deadline, reason}]`.

## Demo customers (`seed.py`)

| id | name | persona | why |
| --- | --- | --- | --- |
| 5 | Sam | 26 · new parent · no goals yet | diapers at DREAMBABY / KRUIDVAT BABY -> suggests "Studies for your child" (2044) |
| 6 | Bas | 31 · saving for a wedding ring | goal "Wedding ring" 3 000 (900 saved); Payconiq with Jurre |
| 7 | Jurre | 29 · drinks with friends · no goals yet | Payconiq to Bas ("drinks"), BLOEMEN purchases -> suggests "Wedding ring" (life + circle) |

`DEMO_IDS = range(1, 8)`.

## Frontend

- `api.ts`: `Suggestion` type; `Customer.suggestions`; `Goal.priority`; `api.addGoal(id, goal)`; `api.onboarding(id, history, goals)`.
- `Onboarding.tsx`: "Set your flight paths". Three parts, top to bottom: (1) Suggested for you (cards with reason + Add),
  (2) Your flight paths: one row per goal with title (editable), target €, per month €, arrive by (date), computed ETA and
  on-course badge, remove; "Add your own" appends an empty row; (3) Spar with your guide: the chat; the draft is sent with
  every turn. Confirm button saves. Plain, SaaS-simple: no bubbles-first layout.
- `Autopilot.tsx`: new prop `onUpdate: (c: Customer) => void`. Shows "Suggested flight paths" (reason + Add) above the
  plan when `c.suggestions.length > 0`; Add calls `api.addGoal` and `onUpdate(view)`.
- `App.tsx` passes `onUpdate={setC}` to `Autopilot`.
