# Try-it-yourself + pipeline: API contract

Shared contract between backend (`src/backend`) and frontend (`src/frontend`). Keep both sides to this shape.

## New endpoints

- `GET /api/scenarios` → `Scenario[]`
  `{ id: string /* a situation id from situations.py */, label: string, blurb: string, needs_goal: boolean }`
- `POST /api/try` body `{}` → `Customer` (a new "You" customer: id in 10000–10999, `name: "You"`, `onboarded: false`,
  `is_try: true`, ordinary life, no goals, no card). Rate-limited (429 with `{error}`).
- `POST /api/customers/{id}/scenario` body `{ "id": "<scenario id>" }` →
  `{ view: Customer, notification: { title: string, body: string } | null }`
  400 `{error}` if the id is not a try customer or the scenario id is unknown. `notification` is null when no card is shown
  (then `view.pipeline` explains why).

## Customer view additions (every customer, demo personas too)

- `is_try: boolean`
- `pipeline: Step[]`, always the same 7 steps in this order:

```ts
type Step = {
  key: "signals" | "understood" | "candidates" | "ai_check" | "score" | "controls" | "decision";
  title: string;      // e.g. "Signals", "What Autopilot understood", "Possible situations", "AI check",
                      //      "Score vs doing nothing", "Your controls", "Decision"
  summary: string;    // one plain-language line, e.g. "2 of 6 situations could apply"
  items: { label: string; value: string; tone: "ok" | "no" | "info" }[];   // detail rows, max ~8
};
```

Examples:
- score item: `{label: "Bill went up", value: "€ 168 × 1.5 goal × 0.90 sure − 3 = 223.8 vs bar 15", tone: "ok"}`
- controls item: `{label: "Deposit matures", value: "Needs your permission", tone: "no"}`
- decision: summary is "Showing one card: …" or "Staying quiet: nothing beat doing nothing".
