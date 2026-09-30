# KBC Mobile — DESIGN.md

Use the impeccable skill for UI and UX ask me questions on how I want it.

> AI-ready design reference for a KBC-inspired banking prototype. Read this file before creating or changing any screen. Apply the same visual language to every page, component, and state.
>
> Status: independent interpretation of public KBC Mobile references, reviewed 30 September 2026. This is not KBC's official internal design system. Exact colours, type sizes, spacing, motion, and component dimensions below are proposed prototype tokens, not verified production specifications.

## 1. Design direction

Create a familiar, calm Belgian banking app: white surfaces, pale blue backgrounds, dark blue text, cyan accents, compact rounded cards, and clear financial information. It should feel helpful, approachable, and dependable.

The interface serves everyday banking, investments, insurance, and practical money tasks. Give users a clear overview and a short path to the next action. Personalisation should change useful content while keeping controls, navigation, and visual structure predictable.

### Publicly observed patterns

- Light app screens with blue text and cyan outline icons.
- A profile avatar, Kate search/help entry, and notification icon at the top of the home screen.
- Horizontal account cards, recent transactions, and a “Voor jou” section.
- Small topic chips such as MyNWS, MyHome, and MyMobility.
- “Mijn KBC” groups products into investments, loans, and insurance using compact white cards.
- Four bottom navigation destinations: Start, Mijn KBC, Beleggen, Aanbod.

These observations come from the public app-store screenshots linked at the end. Promotional backgrounds surrounding phone screenshots are marketing artwork; do not copy their gradients into the banking interface.

### Required design principles

1. Money and the next useful action take priority over decoration.
2. Use one dominant action per card, form step, or dialog.
3. Keep supporting details available through progressive disclosure.
4. Use the same components and tokens across all screens.
5. Keep assistance optional, explainable, and easy to dismiss.
6. Preserve navigation order and financial information when content adapts.

## 2. Colour system

Use these prototype tokens exactly. They are a consistent KBC-inspired palette, not an official brand specification.

| Token | Value | Purpose |
| --- | --- | --- |
| `brand-cyan` | `#00AEEF` | Brand accent, decorative highlights, illustrations |
| `action-blue` | `#006B99` | Primary buttons, links, selected controls |
| `action-hover` | `#00567D` | Hover and pressed primary controls |
| `navy` | `#003B71` | Headings, navigation, account amounts |
| `text` | `#17324D` | Main body text |
| `text-muted` | `#526779` | Secondary labels and descriptions |
| `background` | `#F3F8FA` | App canvas |
| `surface` | `#FFFFFF` | Cards, forms, navigation, sheets |
| `surface-blue` | `#EAF6FC` | Selected chips and assistance panels |
| `border` | `#D9E5EC` | Quiet dividers and card borders |
| `control-border` | `#6C8293` | Input boundaries and unchecked controls |
| `success` | `#167347` | Confirmed success and positive status |
| `success-bg` | `#EAF6EE` | Success message background |
| `warning` | `#805800` | Important caution |
| `warning-bg` | `#FFF5DA` | Caution message background |
| `danger` | `#B42318` | Errors, destructive actions, urgent problems |
| `danger-bg` | `#FFF0ED` | Error message background |

Use darker `action-blue` for white-label buttons and readable links. Bright cyan is an accent, not the default colour for small text on white. Use `control-border` where users must perceive a control boundary; the quiet border is for nonessential separation. Validate contrast in the final rendered interface, including disabled and selected states.

Keep most of each screen white or pale blue. Reserve saturated blue for meaningful emphasis. Do not add purple, neon colours, black fintech panels, or decorative gradients. Financial debit amounts can stay navy with a minus sign; do not make every expense an alarming red.

## 3. Typography

Use a friendly, readable sans serif. The original KBC app font has not been verified. Use supplied licensed KBC fonts if the project already includes them; otherwise use the platform system stack:

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
```

| Role | Size / line height | Weight |
| --- | --- | --- |
| Main balance | 32px / 40px | 600 |
| Page title | 24px / 32px | 600 |
| Section title | 18px / 26px | 600 |
| Card title | 16px / 24px | 600 |
| Body and inputs | 16px / 24px | 400 |
| Supporting text | 14px / 20px | 400 |
| Compact metadata | 12px / 18px | 400 |
| Button label | 16px / 24px | 600 |

- Use sentence case and natural spacing. Avoid all-caps headings.
- Use tabular numerals for balances, transaction amounts, and financial comparisons.
- Keep amounts on one line where possible; allow surrounding labels to wrap.
- Use a Dutch Belgian locale for default demo content: `€ 2.450,00`, `30 sep 2026`, `14:30`.
- Never truncate a payment amount, recipient name on a review screen, or important fee.
- Support larger system text. Fixed heights below are minimums, not clipping limits.

## 4. Spacing, shape, and elevation

Use a 4px spacing grid: `4`, `8`, `12`, `16`, `24`, `32`, `48`.

| Element | Rule |
| --- | --- |
| Mobile page gutter | 16px; 20px on comfortably wider phones |
| Card padding | 16px |
| Compact row gap | 12px |
| Space between cards | 12px |
| Space between sections | 24px |
| Input / button radius | 8px |
| Card radius | 12px |
| Bottom-sheet top corners | 20px |
| Topic chip / avatar radius | Fully rounded |
| Card shadow | `0 2px 8px rgba(0, 59, 113, 0.06)` |
| Dialog shadow | `0 12px 32px rgba(0, 59, 113, 0.14)` |

Prefer a quiet border or subtle shadow. Avoid heavy drop shadows, floating glass panels, nested cards, and giant rounded containers. Related information belongs in one card with rows and dividers.

## 5. App shell and responsive layout

### Mobile

- Design for 390px width and verify at 320px, 390px, and 430px.
- Use a single vertical content column with natural scrolling.
- Home header: 32px avatar, flexible Kate search/help pill, then a notification control. Make their interactive hit areas at least 44px.
- Kate pill copy: “Hoe kan ik je helpen?” Use a small assistant symbol or supplied Kate asset.
- Account cards may scroll horizontally. Leave part of the next card visible and provide an accessible way to navigate the list.
- Keep Start, Mijn KBC, Beleggen, and Aanbod in a stable bottom bar. Use a 24px icon plus a short label, a minimum 56px bar, and bottom safe-area padding.
- Show the selected destination with navy text and a filled icon or clear indicator; use muted icons for inactive destinations.
- On detail screens use a back control, clear title, and relevant actions. Avoid repeating the entire home header.
- Add enough bottom padding that content and primary actions remain visible above fixed navigation and the keyboard.

### Tablet and desktop adaptation

This is a proposed responsive extension, not a reconstruction of KBC Touch.

- Below 768px, keep the mobile navigation and one-column layout.
- From 768px, allow two columns for independent summaries. Keep forms in one readable column.
- From 1024px, use a 224px left navigation with the same four destinations and a content area capped at 1120px.
- Keep form content at a maximum of 560px. Do not stretch a mobile account card across the full desktop width.
- Keep DOM and reading order logical when columns change.

## 6. Core components

| Component | Appearance and behaviour |
| --- | --- |
| Primary button | `action-blue`, white text, 48px minimum height, 8px radius; clear verb label |
| Secondary button | White surface, `action-blue` label and border; same size as primary |
| Text action | `action-blue`; underline on hover/focus; comfortable hit area |
| Icon button | 24px icon inside at least 44px hit area; accessible name |
| Input | Visible label, white fill, `control-border`, 48px minimum height, 8px radius |
| Topic chip | Pale blue pill with icon and label; dark blue selected state if needed |
| Account card | White rounded card; optional short image band; name, masked account number, prominent balance |
| Product row | Category icon, product name, brief detail, optional status, chevron |
| Transaction row | Merchant/recipient left, amount right, date and category secondary; 64px minimum height |
| Status badge | Small semantic tint with icon or word; never colour alone |
| Inline message | Semantic background, icon, short title, practical next step |
| Bottom sheet | White, rounded top corners, title and close control; use for short choices and explanations |
| Review dialog | Summary of the action and its consequences, specific confirmation label, visible cancel |

Use one consistent outline icon family, usually 20–24px with approximately 1.5–2px strokes. Prefer blue icons for banking categories. Do not mix emoji, filled multicolour icons, and outline icons. Use official KBC/Kate assets only when supplied or permitted; otherwise use a text wordmark and a neutral help icon. Never fabricate a KBC logo or claim that a guessed icon is an official asset.

### Interaction states

- Every interactive component needs default, focus, pressed, disabled, and relevant loading/error states. Add hover for pointer devices.
- Focus ring: 2px `action-blue` outline with 2px offset, visible on every surface.
- Loading: maintain layout, use a short label such as “Bezig met laden”, and prevent duplicate submissions.
- Input errors: keep the user's values, identify the field, and explain how to fix it directly below the input.
- Empty state: explain why the list is empty and show one useful action.
- Success: state what happened and provide the result or reference; do not rely on a disappearing toast for important outcomes.
- Stale/offline data: show the last update time and distinguish cached balances from current information.
- Unknown payment outcome: show “Status wordt gecontroleerd”; do not invite a second payment until the outcome is resolved.

## 7. Kate and proactive assistance

The following rules are proposed UX constraints for an AI-enabled prototype. They do not describe KBC's current recommendation policies or establish legal compliance.

Integrate assistance into the familiar “Voor jou” area and Kate entry point. Do not turn the home screen into a chat window or create a fifth navigation tab by default.

### Recommendation card anatomy

1. Small icon and a clear label, such as “Kate tip”.
2. One specific, useful observation.
3. One sentence explaining the evidence or estimated benefit.
4. One primary action; optional “Later” or “Niet relevant”.
5. A discreet but accessible “Waarom zie ik dit?” explanation.

**Example demo card**

> **Hou voldoende saldo voor je huur**  
> Je huur van € 750,00 wordt morgen betaald. Je zichtrekening heeft momenteel € 620,00.  
> **Bekijk opties** · Later  
> Waarom zie ik dit?

Use that copy only when demo data supports it. Opening “Bekijk opties” must explain available choices; it must not silently transfer money.

### Keep personalisation quiet and controllable

- Show at most one proactive recommendation on the initial home view in the prototype. Ordinary account information remains visible.
- Prioritise a meaningful customer benefit and a timely, actionable need. With weak evidence, ask one useful question or show nothing.
- A dismissal removes the card. “Niet relevant” suppresses the same recommendation unless the situation materially changes.
- Present optional notification preferences where appropriate. Do not repeatedly ask after refusal.
- Label sponsored/commercial recommendations and explain relevant fees or conditions before commitment.
- Let users inspect the reason, relevant data, and settings without reading technical model details.
- A recommendation may change its wording and content; it must not move navigation or hide essential controls.
- Keep essential banking tasks usable when optional personalisation is off.

### Action and conversation design

- Use compact answers, structured facts, and relevant action cards. Avoid long chat essays.
- Distinguish facts, estimates, suggestions, and completed actions through clear wording.
- Before a money movement, show amount, source, recipient/destination, date, and known fees in a review step.
- Use “Bevestig overschrijving” instead of a vague “OK”. Provide an equally discoverable cancellation path.
- For a demo, label actions as simulated and use synthetic customer data.
- Show action states accurately: proposed, awaiting confirmation, processing, completed, or failed.
- Offer human assistance when the user asks or when the task cannot be resolved reliably.
- Explanations should mention understandable evidence, such as scheduled payments, rather than a personality label or opaque score.

## 8. Screen recipes

### Start

Header with avatar, Kate entry, and notifications → compact topic chips → account card carousel → recent transactions → “Voor jou” with one useful recommendation → fixed bottom navigation.

Keep balances and everyday banking information in the first view. Put any contextual account action next to the account it affects. Include a discreet balance-visibility toggle when relevant.

### Mijn KBC

Page title → grouped sections for existing products → compact cards/rows with icons and relevant amounts → a small “Nieuw” action per category when needed. Keep investments, loans, and insurance easy to scan.

### Insight detail

Back control and title → observation → supporting transactions or dates → clear impact/estimate → recommended next step → explanation and preferences. Use one simple chart only when it helps understand the finding.

### Financial action review

Back/cancel → action title → amount and destination → relevant conditions → specific confirmation button. After confirmation, show the resulting status with a reference or next step.

### Privacy and notification preferences

Readable section headings → plain-language explanations → individually labelled controls → save feedback. Keep optional settings distinguishable from essential service functions. This is a UX specification; validate legal wording separately before real deployment.

## 9. Writing, charts, and motion

- Default demo UI language: Dutch (Belgium). Keep the entire screen in one language and support localisation to French or English.
- Use direct, friendly language: “Bekijk je uitgaven”, “Pas je limiet aan”, “Probeer opnieuw”.
- Prefer concrete benefits over AI claims. Do not describe internal agents, token budgets, APIs, or model routing in customer flows.
- Use sample data consistently across screens. Never invent a real customer fact to fill a card.
- Chart styling: white/pale blue background, navy labels, blue data series, light gridlines, readable currency/period labels. Include a text summary or accessible data view.
- Use 120–180ms transitions for buttons and 180–240ms for sheets. Use restrained fades or small movements, and honour reduced-motion preferences.
- No confetti for transactions, animated money counters, decorative AI sparkles, or persistent pulsing prompts.

## 10. Accessibility and design checks

- Aim for WCAG 2.2 AA: normal text contrast at least 4.5:1; large text and meaningful control/graphic contrast at least 3:1. Check actual colour pairs.
- Make touch targets at least 44×44px, keyboard actions reachable, and focus visible.
- Use semantic headings, labelled inputs, accessible control names, and status announcements for meaningful updates.
- Do not convey selection, error, or transaction direction through colour alone.
- Support 200% text zoom, longer translated labels, reduced motion, and safe-area insets.
- Never hide essential actions behind hover or an unexplained icon.

Before delivering any screen, confirm:

- [ ] The app is recognisably light, blue, compact, and KBC-inspired.
- [ ] Shared tokens and components match this file.
- [ ] Amounts, recipients, fees, and action states are unambiguous.
- [ ] Each section has a clear purpose and no unnecessary card nesting.
- [ ] Recommendations are useful, explainable, dismissible, and based on available data.
- [ ] Mobile, desktop, keyboard, long text, and loading/error states work.
- [ ] Decorative promotion artwork has not become the app's background style.

## 11. Instructions for an AI builder

Treat this file as the visual and UX reference for every UI task. Reuse existing project components where they fit these rules. If a necessary pattern is missing, derive it from these tokens and the closest existing component; do not introduce a new visual style.

If supplied KBC brand assets or explicit project requirements conflict with a proposed token, follow the supplied authoritative reference and update the affected token consistently. Do not describe proposed values as official KBC specifications.

**Reusable prompt**

> Read DESIGN.md before designing or coding. Build the requested KBC-inspired app screens using its colours, typography, spacing, navigation, and components. Keep the interface simple, mobile-first, accessible, and consistent. Integrate Kate assistance through compact, explainable action cards. Use synthetic data and label simulated financial actions. Include useful loading, empty, error, and confirmation states. Do not add decorative gradients, extra navigation, or unsolicited recommendation feeds.
