# KBC Autopilot ("situations, not segments"): proof of concept plan

## Context

**The KBC challenge.** Show a scalable personalization approach for 2.3M+ customers. It should be a new way of understanding and guiding customers, not another feature.

**Decisions so far:**
- **Framing:** "Situations, not segments". The idea has to visibly work for *every* customer.
- **Stack:** React frontend and a Python backend, with as few frameworks and dependencies as possible.
- **Delivery:** a **proof of concept that the jury uses at a public URL on Google Cloud**. The code lives in a public repo, so no keys in files. It doesn't need to be production-ready.
- **Tone:** it must feel like a **helping tool, not a KBC sales pitch**. The goal is a solid mix of customer value and KBC value.

### How the plan answers the challenge's 5 questions

| Challenge question | Our answer |
|---|---|
| 1. Which signals show what customers need? | **Three kinds:**<br>• transactions and events (price increases, club fees, PIN resets, maturities, forecasts)<br>• **goals the customer states** (onboarding)<br>• customer responses (Later / Not relevant / accepted) |
| 2. How do we recognise situation, behaviour and intent? | **Situations, not segments.**<br>• Code features act as a prefilter.<br>• Jev (a fast AI classifier) then screens the remaining customers with typed yes/no questions, e.g. "is this a sports club?" or "does this help goal Y?".<br>• Intent comes from the confirmed flight plan (the customer's goals). |
| 3. How do experiences adapt automatically? | **One scoring rule for every situation:**<br>• customer € × goal weight × confidence − annoyance − risk, compared against "do nothing".<br>• The system learns from each response.<br>• Mode and consent toggles are respected.<br>• "Always do this" rules act as the autopilot. |
| 4. How does it work across products and channels? | **One catalogue spans all of KBC and beyond:**<br>• banking, insurance, Bolero and investing (handed to an advisor), mutualiteit (health insurer), government, family volmacht (power of attorney)<br>• human advisor handoff when needed<br>• the same decision object is shown in the app card, Kate or an advisor's screen |
| 5. Impact for millions at once? | **Scale comes from configuration, not code:**<br>• a new situation is one catalogue row, which the jury can add live;<br>• the funnel runs over the whole population, with cost per layer (Jev at $0.042 per million tokens);<br>• a holdout group measures customer € and KBC €. |

### The idea in one sentence

**KBC Autopilot:**
1. You tell it what you're working toward, in a 2-minute chat.
2. From then on it watches for situations that matter to *your* goals.
3. It shows one card only when that card clearly helps, and otherwise stays quiet.
4. It never acts without your approval.

You're the pilot. Autopilot handles routine work only on rules you've approved once. KBC doesn't need 2.3M journeys or 20 segments, just **one engine**. **A new situation is one row of configuration, not a new project.**

## Onboarding: "Where do you want to fly to?" (LLM goal sparring)

**The gimmick: framing plus one route visual** (user decision). It stays restrained, as DESIGN.md requires.

- **Opening line:** "Where do you want to fly to?" Destination chips help people start: House, Travel, Safety buffer, Studies, Own business, Family, Other. Each chip gets a DESIGN.md outline icon, no emoji.
- **The flight plan maps onto goals:**

  | Flight term | Meaning |
  |---|---|
  | **Destination** | Each long-term goal |
  | **Stopover** | Each immediate goal (next 3 months) |
  | **ETA** | Projected arrival date, computed in code from the current saving pace |
  | **Status: On course / Off course** | The goal-off-track situation reuses the same wording |
  | **Flight plan** | The whole goal list |

- **One visual:** a single, static, horizontal route line. It runs from "Today", through the stopover dots, to the destination dot. Under each dot: title, € progress / target, ETA.
  - Inline SVG, `brand-cyan` for the line, `navy` for labels.
  - No plane animation, no gradients, no confetti.
  - The same component appears later on the Autopilot page.
- **"Confirm flight plan"** is the one primary action. The customer is the pilot, and nothing is saved until confirmed.
- **Where the metaphor lives:** only in onboarding and on the Autopilot/goals page. Banking screens, cards and review steps use plain language.

**Layout:** chat plus a live flight plan in one phone column (mobile-first).
- The chat thread sits on top.
- A compact flight-plan panel is pinned below it and updates after each LLM turn. It shows the route line and the goal rows.
- From 768px the chat and the flight plan sit side by side.

**Session:** a short chat, skippable, capped at 6 turns. The LLM asks about:
- **Immediate goals** (next 3 months), e.g. "don't go into the red before payday", "€600 for a ski trip in February", "pay off the dentist bill".
- **Long-term goals**, e.g. "€40k house deposit by 2030", "a buffer of 3 months' expenses", "raise €150k for my startup", "support my mother's finances".

The LLM also sees a pseudonymised summary of the customer's income and spending, so it can challenge unrealistic targets. For example: "At your current savings rate that takes 7 years. Want to aim for 2031 or look for room in your budget?"

**Structured output.** Every turn returns a reply plus a draft of the goals:

```json
{"reply": "...", "goals": [{"horizon": "now|long", "type": "save_for|buffer|avoid_overdraft|pay_off|budget_cap|raise_capital|care_for_family|other",
  "title": "Ski trip", "target_eur": 600, "deadline": "2027-02-01", "priority": 1}]}
```

**Checks in code:**
- Enum values, amounts from 0 to €10M, deadlines in the future, and at most 5 goals.
- If the output is invalid, we re-ask once and then fall back to the goal-chip form.

**Human in the loop.**
- Goals are saved only after the user taps "Confirm flight plan".
- Goals can be edited later, and they appear in the Memory panel with a reset button.

**How goals change the engine.** This is also what makes Autopilot feel like help rather than sales.
- **Goal-linked cards score higher.** If a situation moves a confirmed goal forward, `customer_eur` gets a goal weight of ×1.5 for priority 1.
  - Whether a situation serves a goal is one extra Jev Noul (yes/no) per goal inside the same fan-out call: "does acting on X help goal Y?"
- **New help situations, all driven by goals:**
  - "goal off track": the projected date slips past the deadline;
  - "goal reached";
  - "spending room to top up a goal".
- **The card says which goal it serves**, e.g. "This helps: Ski trip (€420 / €600)".

**Standing rules: the "autopilot" part, and still human in the loop.**
- On low-risk help cards the user can tap **"Always do this"**, e.g. "move anything above €1,500 on my current account to Ski trip every month".
- The engine then runs the rule, logs each run, and notifies afterwards.
- Limits:
  - only transfers between the customer's own accounts;
  - a monthly cap in €;
  - it can be revoked in one tap from Memory.
- It is never available for product, regulated or credit actions.

**Demo safety for the jury:**
- Onboarding is the second live AI endpoint, so it is rate-limited: 30 messages per IP per 10 minutes, 6 turns per session, and a 500-character cap per message.
- If there's no key or the limit is hit, a goal-chip form produces the same JSON. The demo never gets stuck.
- The 4 demo customers come with goals already confirmed, so the jury can skip onboarding. A "Start as new customer" button runs the chat.

## UI and UX: DESIGN.md + impeccable (binding)

`DESIGN.md` at the repo root is the visual authority. It is a KBC-inspired prototype system. Every screen reads it before any code is written, and the `impeccable` skill drives the build.

- **Language (user decision): English UI with an NL/FR toggle.**
  - One `strings.ts` dictionary per language.
  - Amounts and dates stay in the Belgian format (`€ 2.450,00`, `30 sep 2026`).
  - The LLM wording and the onboarding reply follow the selected language.
- **App shell:** a phone frame on desktop, full screen on mobile.
  - **Header:** avatar, the Kate pill "How can I help?", and notifications.
  - **Topic chips:** these include **Autopilot**, next to MyHome and MyMobility.
  - **Bottom bar:** 4 tabs (Start, My KBC, Invest, Offers). **No fifth tab**, per DESIGN.md.
- **Start screen,** following the DESIGN.md recipe, in this order:
  1. account cards
  2. recent transactions
  3. **"For you"** with **at most one Autopilot card**
  
  Balances stay in the first view.
- **Card anatomy** (DESIGN.md §7):
  - label "Autopilot tip", one observation, one sentence of evidence or € benefit;
  - **one primary action**, plus "Later" and "Not relevant". These replace Not now and Never.
  - "Why am I seeing this?" opens a bottom sheet. It shows the signals and data used, confidence in plain words, and "Includes a KBC product" when relevant.
  - The card also says "This helps: {goal}" and "Doing nothing is fine too".
- **Money movements** always go through a review screen: amount, source, destination, date, fees. The button reads **"Confirm transfer"** and the screen is labelled **Simulated**. The "Always do this" rule uses the same review step.
- **Autopilot page** (opened from the chip):
  - flight plan with route line, goals and ETAs;
  - active rules with revoke;
  - mode (quiet / normal / proactive);
  - consent toggles;
  - memory with reset;
  - the "What Autopilot considered" list, with DO_NOTHING as a row;
  - the € created total as static text. There is **no animated counter and no confetti** (DESIGN.md §9). "Goal reached" is a plain success message.
- **Engine view for the jury:** "Behind the scenes", a separate desktop page outside the phone shell, same tokens. It holds the catalogue, add-a-situation and the funnel. This is the only place that uses technical wording, because DESIGN.md bans agent and model terminology in customer flows.
- **States:** loading, empty ("Autopilot has nothing for you right now, and that's fine"), error, and the LLM or rate-limit fallback to chips. All must be designed.
- **Accessibility:** 44px touch targets, visible focus, reduced motion, 320–430px widths.
- **Impeccable flow:**
  - Run `impeccable init` first to write `PRODUCT.md` from this plan's confirmed context.
  - Then run new-work inside the existing DESIGN.md world, with no redesign.
  - Read `craft-floor.md` before UI edits.
  - Finish with one batched verification pass at desktop and mobile.

### How the demo proves it works for everyone

1. **Situations are data.**
   - About 12 catalogue rows cover families, students, seniors, entrepreneurs, savers and everyone else.
   - The engine code never mentions football or the staatsbon (Belgian state savings bond).
2. **The jury adds a situation live.**
   - A juror types e.g. "customer recently got a pet".
   - Jev screens 200 synthetic customers in a few seconds and shows the matches.
   - No code changes.
3. **A population funnel over 2,000 synthetic customers** shows each stage:
   - candidates
   - Jev-confirmed
   - shown
   - left alone on purpose
   - € for customers
   - € for KBC (compared against a holdout group)
   - AI cost extrapolated to 2.3M

### What's new compared with Kate today

Researched 2026-09-30; sources are in the research doc.
- **Kate today** has about 140 fixed, rule-based proactive scenarios and on/off consent switches: "Extra gebruiksgemak" (extra convenience) and "Op jouw maat" (tailored offers).
- **Not visible to customers today:**
  - "Do nothing" as the default every card must beat.
  - Situations written in plain language.
  - Approve / Not now / Never on every card, with memory the customer can see and reset.
  - Quiet / normal / proactive modes.
  - A "€ created for you" total.
  - Cash-shortage forecasts.
  - Subscription price-rise alerts.
  - Outside services such as a mutualiteit (health insurer) refund.
- **Pitch caveat:** say "not visible today". KBC may have internal tooling we can't see.

## Helper first, KBC second: the balance built into the engine

**Principle: helping earns trust, and trust earns the right to suggest a product.**

The research supports this:
- Loyal "promoter" customers are worth 2–2.5x more than detractors (Bain).
- Sending fewer, better notifications raised click-through by 11–31% (Pinterest).
- Customer inattention is a margin that regulators are taking away anyway (UK Consumer Duty, EU Retail Investment Strategy).

The rules are enforced in code, not just in copy:
1. **Two kinds of cards.**
   - `help` cards: cash shortage, price rise, duplicate charge, refund, volmacht (power of attorney), subsidy, student job hours.
   - `product` cards: savings rule, term account, insurance check, investment.
   - The catalogue has about 3 help rows for every product row, and the funnel shows the ratio actually shown.
2. **The customer's benefit decides.**
   - The score uses only `customer_eur`.
   - `kbc_eur` is logged for the business case but never raises a card's rank.
   - A card is shown only if `customer_eur > 0`.
3. **Product cards clear a higher bar.**
   - They get an extra annoyance penalty, so they need more customer value to beat "do nothing".
   - Frequency caps:
     - at most one product card a month;
     - after a customer rejects one, product cards pause for 60 days;
     - help cards are capped at one a week, while critical cards (e.g. a cash shortage) always show.
4. **Consent mirrors KBC's real settings.**
   - Help cards need "Extra gebruiksgemak".
   - Product cards also need "Op jouw maat".
   - Both are toggles in the demo.
5. **Honest options.**
   - Product cards show the relevant alternatives, including non-KBC ones. For example, a maturing deposit card lists the staatsbon too.
   - The KBC option comes pre-filled, so it's one tap, but it isn't the only option.
   - The card is clearly labelled "Includes a KBC product".
6. **Tone rules for the LLM** (and the templates):
   - State the fact, the € for the customer, and the options. That's all.
   - No urgency, no exclamation marks, no "offer" or "exclusive".
   - Every card ends with "Doing nothing is fine too".
   - Phrasing that breaks these rules is rejected and the template is used instead.
7. **"Already covered" cards are kept deliberately.**
   - An example is "Your child's club already insures them; claim €50 from your mutualiteit".
   - These cost KBC a sale, and the funnel counts them as trust investments.

### Does it make KBC money? (checked by 3 agents)

**Moderately positive, if the conditions below hold.** The best evidence:
- DBS reports about S$1B of AI/data value, measured against control groups, roughly 4–5% of its income. That figure also includes fraud, credit and productivity gains.
- Kate today: 400k+ products sold a year, a 13.6% lead conversion rate, and the work of about 400 FTE.

**Risks to say out loud:**
- Nudging idle cash erodes deposit margin; apps already reduce the value of a bank's deposit base by 14–22%.
- "Already insured" cards cost KBC insurance sales.
- No bank has isolated next-best-action profit on its own.

**KBC's proof point:** it lost €5.7bn in deposits to the 2023 staatsbon and spent about €87m in interest income winning it back. The biggest lever is keeping deposits at KBC before a competitor or the state reaches the customer. The design keeps money in KBC by default, while staying honest about the alternatives.

**Belgian business case** (1M users, 2% shown a card per week; * = assumption):

| | Low | Base | High |
|---|---|---|---|
| Accepted actions per year* | 15.6k | 83k | 234k |
| Cross-sell and retention | €0.3m | €4.2m | €21m |
| Deposits defended (0/10/20% of €5.7bn × 1.5%)* | €0 | €8.6m | €17m |
| Fewer support contacts | €0.4m | €0.8m | €1.6m |
| AI tokens | –€0.1m | –€0.2m | –€0.5m |
| Build, run and compliance* | –€8m | –€5m | –€3m |
| **Net per year** | **–€7.4m** | **+€8.4m** | **+€36m** |

A 10% holdout group in the synthetic data shows how KBC would measure this for real.

## Architecture: one pipeline for every situation

```
txns/events ─▶ 1. CODE features (forecast min balance, recurring price Δ, idle cash, PIN resets 30d, maturity days, …)
            ─▶ 2. CODE prefilter per situation → candidates
            ─▶ 3. JEV screen: 1 fan-out call per candidate customer, a Noul (yes/no) per situation → confidence
            ─▶ 4. CODE decide: score = customer€ × goal_weight × confidence − annoyance(kind, prefs, mode) − risk ; DO_NOTHING = 0
                  standing rules that match → execute within cap, log, notify after
                  + consent gate + frequency caps; critical always surfaces
            ─▶ 5. LLM phrase (shown cards only): rewords the frozen decision; must keep exact €, pass tone rules, else template
            ─▶ 6. CUSTOMER: Approve / Not now / Never → prefs + decision log + € counters; regulated → advisor handoff
```

- **Jev** answers typed yes/no questions and costs $0.042 per million tokens.
- **Code** does all the maths, because Jev can't.
- **The LLM** never picks the action or the amount.
- **Guardrails:**
  - Credit and investment situations are `regulated`, which forces a handoff to a human advisor (AI Act high risk; MiFID).
  - No health inferences (GDPR Art. 9): rows describe behaviour, never diagnoses.

```python
@dataclass(frozen=True)
class Situation:
    id: str; audience: str; kind: Kind            # HELP | PRODUCT
    prefilter: Callable[[Features], bool]
    question: str                                 # Jev Noul over pseudonymised state
    customer_eur: Callable[[Features], float]     # drives the score
    kbc_eur: Callable[[Features], float]          # logged only; may be negative
    risk: Risk                                    # CRITICAL | NORMAL | REGULATED
    action: Action                                # APPROVE_TRANSFER | PREFILL_FORM | INFO | HANDOFF
    template: str
```

### Catalogue (★ = seeded demo customer)

| Kind | Situation | Action |
|---|---|---|
| help | ★ Cash shortage forecast within 14 days | Approve a transfer from your own savings (critical) |
| help | ★ Recurring bill up more than 5% | Show the increase plus ways to compare, including non-KBC |
| help | Duplicate charge | Info plus dispute |
| help | ★ Child's sports club fee | "Already insured via the federation; claim €50 from your mutualiteit", with the form pre-filled |
| help | New childcare or school payments | Groeipakket (Flemish child benefit) check |
| help | Student job hours near the 650-hour limit | Info |
| help | ★ Goal off track (projected date past deadline) | Show the gap plus options: move the date, move €X, or a spending tip |
| help | Room left in this month's budget | Approve moving €X to the goal, or "Always do this" |
| help | Goal reached ("Arrived") | Plain success message, then the next stopover (only if the customer has another goal) |
| help | ★ 3 or more PIN resets in 30 days | Family volmacht (power of attorney) plus a care advisor handoff |
| product | Idle cash above a buffer for 90 days | Options, with KBC "Automatisch sparen" (automatic saving) pre-filled |
| product | Deposit or staatsbon maturing within 30 days | After-tax comparison: KBC term account, savings, staatsbon. The Bolero (KBC's online broker) part goes to an advisor |
| product | Address change | Home insurance check (may conclude "you're covered") |
| product | SME cash runway under 3 months | Handoff to a business banker (regulated) |

## Hosting: public URL on Google Cloud, no secrets in the repo

- **Cloud Run, a single container.**
  - The `Dockerfile` builds in two stages: first `node:22` runs `npm ci && npm run build`, then `python:3.12-slim` copies in `backend/` and `frontend/dist`.
  - Deploy command:
    ```
    gcloud run deploy kbc-autopilot --source . --region europe-west1 --allow-unauthenticated \
      --min-instances 1 --max-instances 1 --set-secrets OPENROUTER_API_KEY=openrouter-key:latest
    ```
  - `max-instances 1` means everyone shares one SQLite state. `min-instances 1` means no cold start while the jury uses it.
- **The key lives in Google Secret Manager.**
  - Create it once with `gcloud secrets create openrouter-key --data-file=-`.
  - Cloud Run passes it to the app as an environment variable.
  - The repo has no `.env` or `.env.example`. Locally, run `export OPENROUTER_API_KEY=…` in your shell (optional).
  - `.gitignore` already covers `.env*`.
  - Set a hard spend cap on the OpenRouter key (e.g. $10) in the OpenRouter dashboard. That is the real backstop for a public URL.
- **Pre-warmed AI answers.**
  - Run `python backend/seed.py --warm` locally, once, with the key.
  - This writes the Jev screening answers and the LLM wording for the 2,000 customers into `backend/ai_cache.json`, which is committed.
  - The data is synthetic, so the file has no secrets and no PII.
  - Result: browsing customers makes no AI calls and is instant. Without a key, the whole demo still works except the live add-situation.
- **Abuse limits on the one live endpoint (add-situation):**
  - input capped at 200 characters;
  - 3 requests per IP per 10 minutes;
  - 30 per hour in total;
  - a 200-customer sample;
  - the text only ever becomes a Jev question.
- **Resetting the demo:**
  - The DB is created fresh from the seed on every container start.
  - A "Reset demo" button restores it, so jurors can't break it for each other.

## Files (all new; backend uses only the Python standard library, frontend only react and react-dom)

| File | What it does |
|---|---|
| `backend/schema.sql` | Tables:<br>• `customer` (pseudonymous key, mode, consent flags, holdout)<br>• `txn`<br>• `event`<br>• `goal` (horizon, type, title, target, deadline, priority, confirmed)<br>• `rule` (standing autopilot rules: goal, threshold, monthly cap, active)<br>• `prefs`<br>• `decision` (also serves as the audit log)<br>• `situation_custom` |
| `backend/onboarding.py` | `turn(history, summary)`: calls the LLM through OpenRouter with a system prompt limited to financial goals. The prompt tells it to write no sales copy and to push back on unrealistic targets. The reply is parsed as JSON and checked against the goal schema; if that fails it asks once more, then falls back to the chips form. |
| `backend/seed.py` | Builds a fresh SQLite DB with 2,000 customers from a fixed `random.seed`, plus the 4 demo customers. With `--warm` it also fills `ai_cache.json`. |
| `backend/situations.py` | The catalogue. |
| `backend/engine.py` | Pure functions: `features`, `candidates`, `decide` (score, consent, caps, holdout) and `respond_update`. |
| `backend/ai.py` | `screen()`: Jev fan-out on a thread pool of 40, using `urllib` to call OpenRouter.<br>`phrase()`: the LLM call (`anthropic/claude-haiku-4-5`), which checks the amount and the tone rules.<br>Both read from `ai_cache.json` first and fall back to keyword matching or the template. |
| `backend/server.py` | Built on `ThreadingHTTPServer`. Endpoints:<br>• `GET /api/customers`<br>• `GET /api/customers/{id}`<br>• `POST /api/customers/{id}/respond`, `/mode`, `/consent`, `/reset`<br>• `POST /api/situations` (rate-limited)<br>• `POST /api/onboarding/turn` (rate-limited)<br>• `POST /api/customers/{id}/goals` (confirm or edit)<br>• `POST /api/customers/{id}/rules` (create or revoke)<br>• `GET /api/funnel`<br>• `POST /api/reset-demo`<br><br>It also serves `frontend/dist`, validates every body and caps its size, sets basic security headers, and listens on `$PORT`. |
| `backend/test_engine.py` | `unittest` checks:<br>• the shortfall forecast<br>• price-rise detection<br>• DO_NOTHING wins below the threshold<br>• Never suppresses non-critical cards only<br>• the product-card cap and the pause after a rejection<br>• a product card needs "Op jouw maat"<br>• `customer_eur <= 0` is never shown<br>• holdout customers never see cards<br>• regulated cases hand off<br>• no PII in the AI state<br>• LLM text with the wrong amount or with urgency words is rejected<br>• invalid goal JSON is rejected (bad enum, past deadline, more than 5 goals)<br>• goal weight lifts a card that serves a goal<br>• off-track projection<br>• a standing rule respects its monthly cap, runs only between own accounts, and can't attach to product or regulated situations |
| `frontend/` (Vite React TS) | Only `react` and `react-dom` as dependencies. Tokens from DESIGN.md go in one `tokens.css`, and the UI strings in `strings.ts` (EN/NL/FR). Screens are switched with a `useState` view switch, not a router:<br>• `Onboarding`: chat, `FlightPlan` route line, and destination chips<br>• `Start`: shell, account cards, transactions, "For you" card<br>• `Review`: confirm transfer<br>• `WhySheet`: "Why am I seeing this?"<br>• `Autopilot`: flight plan, rules, mode, consent, memory, "considered" list<br>• `BehindTheScenes`: catalogue, add-a-situation, funnel<br><br>Shared components come from DESIGN.md §6: button, card, chip, row, inline message, bottom sheet. |
| `PRODUCT.md` | Written by `impeccable init`, from this plan. |
| `Dockerfile` | Two-stage build. |
| `README.md` | Local run, the deploy command, the secret setup, and the OpenRouter spend cap. |
| `group/ideation/2026-09-30-research.md` | Novelty table, prior art, profit evidence and business case, Belgian facts, and source URLs. |

**Skipped (it's a proof of concept):**
- Auth.
- Postgres.
- Real integrations (mutualiteit, Bolero, volmacht). These are mocked, each marked with a `ponytail:` comment.
- Multi-instance state.
- Clustering, graph and vector DBs.

## Pitch flow (3 minutes)

1. **Problem:** banks segment people, but people live in situations and have goals.
2. **"Where do you want to fly to?", live, 30 seconds:**
   - A new customer answers "skiing in February, and one day my own flat".
   - The LLM pushes back on the flat's timeline.
   - The route line fills in: Today → Ski trip (stopover) → Flat (destination, ETA 2031).
   - The customer taps "Confirm flight plan".
3. **Tom:** a bill went up €14 a month.
   - It's a help card. The "considered" view shows 11 situations left silent.
   - The card in "For you" says "This helps: House deposit". Tapping "Why am I seeing this?" shows the evidence.
   - He compares the options and moves the €168 a year he saves to his goal. The ETA on his flight plan moves forward.
   - He sets "Always do this" on a surplus sweep through the review step. That's the autopilot engaged.
4. **Toggle "Op jouw maat" off:** product cards disappear and help cards stay. The customer is in control.
5. **Grandma:** a volmacht card appears, and the case is handed off to a human.
6. **The jury adds a situation live.**
7. **Funnel:**
   - most customers are left alone;
   - a 3:1 ratio of help to product cards;
   - € for customers, and € for KBC compared with the holdout group;
   - AI cost per day.
8. **Business case, and the €5.7bn staatsbon lesson:** help first, and deposits stay at KBC.
9. **Trust:** Approve on every card, "why", visible memory, revocable rules, and built-in guardrails.

## Build order

1. `schema.sql` → `seed` → `engine` + `test_engine`.
2. `ai` and `onboarding`, both with cache and fallbacks. Then run `seed --warm` and commit `ai_cache.json`.
3. `server`.
4. UI via impeccable:
   1. `init`, which writes `PRODUCT.md`.
   2. `tokens.css` and the shared components.
   3. Screens in this order: Start + "For you" card + Why sheet + Review, then Onboarding + FlightPlan, then the Autopilot page, then Behind the scenes.
   4. One batched check at 320, 390 and 430px and on desktop.
5. `Dockerfile` → Secret Manager → Cloud Run deploy → test the public URL.
6. Research doc and README.
7. Aikido scan (10% of the grade): no secrets in git, parameterised SQL, input validation and limits, security headers, npm CVEs.

## Verification

- `cd backend && python -m unittest` passes.
- Local run: `cd frontend && npm ci && npm run build && cd ../backend && python server.py`, then open `localhost:8000`. It must work **without** `OPENROUTER_API_KEY`.
- Walkthrough:
  - The 4 demo customers show the expected cards.
  - Approve, Not now and Never behave as specified.
  - Turning off "Op jouw maat" hides product cards.
  - Quiet mode silences non-critical cards.
  - PIN resets lead to a handoff.
  - "Reset demo" restores the state.
  - Onboarding: the chat fills the flight plan live, and "Confirm flight plan" saves it. The customer's cards then show "This helps: …". Without a key, the destination chips produce the same result.
  - EN/NL/FR toggle: every screen switches language completely, and amounts stay in the Belgian format.
  - DESIGN.md checklist (§10) holds for every screen:
    - at most one "For you" card;
    - no fifth tab;
    - no animated counters or confetti;
    - the review step comes before any transfer.
  - "Always do this" creates a rule. The rule runs on the next evaluation within its cap, and revoking it stops it.
- On the Cloud Run URL: open it in a private window on a phone.
  - Add a situation live and confirm it returns matches.
  - The 4th request within 10 minutes is refused.
  - `git grep -i "sk-or"` returns nothing.
- Aikido shows no high findings.
