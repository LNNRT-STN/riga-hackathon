# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + TypeScript front end (only `react` and `react-dom` at runtime); Python standard-library back end with SQLite; hosted as one container on Google Cloud Run. Chosen by the team: as few frameworks and dependencies as possible.

## Users

- **KBC retail customers** (demo personas): people with everyday money lives and goals, such as saving for a home, a trip, a safety buffer, or helping family. They open the app to bank, not to be sold to.
- **The hackathon jury (KBC)**: opens a public URL, switches between demo customers, and must understand within minutes how the mechanism scales to 2.3M customers.

## Product Purpose

KBC Autopilot is a proof of concept for a new way KBC understands, supports, and guides customers at scale. The customer states where they want to go ("Where do you want to fly to?"), and Autopilot watches for situations that matter to those goals. It shows at most one card when it clearly helps, stays quiet otherwise, and never acts without approval. Success: each demo customer gets one relevant, explainable card; the jury sees one engine serve every customer.

## Positioning

Situations, not segments. One scoring rule for every customer: customer value × goal weight × confidence − annoyance − risk, compared against "do nothing". A new situation is one catalogue row, not a new project. Help comes first; a KBC product only appears when it is the honest best option, and it is labelled.

## Operating Context

Demo on a public Cloud Run URL, used by a jury on laptops and phones. All customer data is synthetic. Money movements, forms and advisor calls are simulated and labelled as such. AI (Jev for yes/no screening, an LLM for wording and onboarding) runs through OpenRouter when a key is present in the environment; an offline fallback keeps every flow working without it.

## Capabilities and Constraints

- First version is English only; NL/FR follow later.
- Six situations wired end to end: cash shortage ahead, bill went up, sports club fee refund, trouble logging in, room to top up a goal, deposit matures.
- Human in the loop: every money movement goes through a review step; "Always do this" rules are own-accounts only, capped and revocable.
- Customer controls: Later, Not relevant, mode (quiet / normal / proactive), consent toggles mirroring KBC's "Extra gebruiksgemak" and "Op jouw maat", visible and resettable memory.
- No secrets in the repo; the key comes only from the environment (Secret Manager on Cloud Run).

## Brand Commitments

Visual language follows `DESIGN.md` (KBC-inspired prototype system, not an official KBC design system). No official KBC logo or Kate assets are available; use a text wordmark and neutral icons. The flight metaphor ("Where do you want to fly to?", destination, stopover, ETA, on course) lives only in onboarding and on the Autopilot page.

## Evidence on Hand

Research notes in `group/ideation/2026-09-30-research.md` (Kate's current capabilities, prior art, business case). No real customers, testimonials or KBC performance claims may be invented; demo figures are synthetic and labelled.

## Product Principles

1. Doing nothing is a valid answer; silence is the default a card must beat.
2. Help first, KBC second: customer value ranks cards, KBC value is only logged.
3. Explain everything: every card shows why, which data, and how sure.
4. The customer is the pilot: approval, easy dismissal, and revocable rules.

## Accessibility & Inclusion

WCAG 2.2 AA per DESIGN.md: 4.5:1 text contrast, 44px targets, visible focus, reduced motion, 320–430px mobile widths. Seniors are a core audience: plain language, no diagnoses or labels about people.
