---
name: simple-ui-ux
description: Design, redesign, critique, or specify simple, restrained user experiences and interfaces for software products. Use for websites, mobile or desktop apps, internal tools, consumer products, and developer tools; do not use for code-only implementation work without an interface decision.
---

# Simple UI/UX

Design software interfaces with radical simplicity. Treat every element as guilty until proven necessary.

## Core rule

Make the product feel obvious. If an element, option, label, decoration, screen, or piece of copy can be removed without harming the user's task, remove it.

Prefer fewer decisions, fewer screens, fewer controls, fewer words, and fewer visual treatments. This applies to new products, existing interfaces, and internal software alike.

## Design priorities

Apply these priorities in order:

1. **Clarity** — users should immediately understand the current screen's purpose.
2. **Task completion** — optimize for the user's job, not feature exposure.
3. **Hierarchy** — give each screen or state one clear focal point.
4. **Reduction** — remove secondary UI before adding new UI.
5. **Consistency** — reuse established patterns rather than inventing variants.
6. **Calmness** — make the interface feel controlled, spacious, and quiet.
7. **Polish** — use detail to improve understanding, never as decoration.

## Structure and behavior

### Give each screen one primary purpose

Define the screen's main job and make it dominant. When an action is needed, use one primary action. Demote genuinely secondary actions to subtle text actions, contextual menus, or a later step.

Do not give unrelated actions equal visual weight. Keep navigation shallow, predictable, and labelled with short concrete words. Do not create categories that contain one item or duplicate destinations without a clear reason.

### Show choices only when they matter

Use strong defaults for common cases. Progressively disclose infrequent, advanced, or irreversible options. Ask for information at the moment it becomes useful rather than front-loading setup, preferences, tours, or checklists.

Use confirmation for consequential or hard-to-reverse actions; do not interrupt ordinary, low-risk, reversible work with dialogs.

### Use hierarchy before containers

Create structure primarily with spacing, typography, alignment, grouping, and scale. Add borders, cards, shadows, dividers, tabs, badges, or icons only when they communicate a real distinction or action.

Keep surfaces mostly neutral and the accent palette limited. Reserve strong color for the primary action, important status, or errors. Use status colors to communicate status, not decoration.

### Keep content brief and actionable

Use plain, specific labels and short headings. Remove marketing language, redundant subtitles, generic helper text, and explanations the interface itself can make unnecessary.

An empty state should say what is missing and offer the next useful action. A form should ask only for information needed now, use sensible defaults, group related fields, and move optional detail out of the main path.

### Design data views for decisions

Do not use a dashboard grid merely because data exists. Show summaries and metrics only when they influence a decision or action. In tables and lists, show the fields users need to scan, compare, or act; reveal the rest on demand. Keep row actions contextual and use badges only when the state matters.

### Respect the interaction context

Apply the same reduction principle across responsive web, mobile, desktop, touch, keyboard, and assistive-technology use. Preserve clear focus, readable contrast, usable target sizes, logical reading order, and keyboard access. Do not trade accessibility or error prevention for visual minimalism.

## Visual character

Aim for generous whitespace, precise alignment, restrained typography, neutral surfaces, limited accent color, subtle separators, compact deliberate copy, and simple iconography only when it improves recognition.

Favor a premium, controlled feeling over decoration. Inspiration may come from products known for restraint and clarity, but do not copy proprietary assets or distinctive branded compositions.

## Simplify by default

Challenge or reduce these patterns unless they directly support the user's task:

- card-on-card layouts and equal-weight widget grids
- decorative gradients, glass effects, glows, and busy backgrounds
- several competing accent colors or primary actions
- giant hero sections inside task-oriented software
- labels, icons, badges, and helper text all saying the same thing
- deeply nested navigation, excessive tabs, or settings shown before needed
- tooltips compensating for unclear controls
- modal dialogs for ordinary navigation
- forced tours and filler-heavy empty states
- animation that does not clarify state, feedback, or movement

## Decision test

Before accepting a design decision, ask:

1. What user task does this support?
2. Is it necessary now?
3. Can it be removed, combined, or handled with a strong default?
4. Can spacing, typography, or placement create the hierarchy instead of another component?
5. Is the next action immediately obvious?
6. Can a first-time user understand it without an explanation?

Simplify again when an answer exposes unnecessary complexity.

## Output behavior

When proposing or critiquing a UI/UX change, lead with the primary user task and the simplest viable structure. Describe only the elements needed to complete that task, explicitly identify what should be removed from existing designs, and recommend one direction unless alternatives materially affect the user's goal.

For implementation work, pair this design guidance with the repository's engineering and UI-craft instructions. Do not prescribe frameworks, CSS architecture, or component APIs unless the request requires them.
