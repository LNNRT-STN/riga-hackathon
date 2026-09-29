# Riga Hackathon

Shared workspace for the Riga Hackathon team. The product brief is still to be
defined; add only team-confirmed decisions to `PRODUCT.md` once it exists.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/` | Application source code. |
| `group/ideation/` | Problem research, decisions, and product notes. |
| `group/presentation/` | Pitch, demo, and presentation material. |
| `AGENTS.md` | Required contributor and agent workflow. |

## Getting started

1. Clone the repository and open it in your editor.
2. Read `AGENTS.md` before making changes.
3. Keep local credentials in `.env`; never commit them. Copy from `.env.example`
   when the project adds one.
4. Record confirmed product context in `PRODUCT.md` before the first design task.

There is currently no application runtime or dependency manifest. Add the
smallest setup command here when the team chooses the stack.

## Working together

- Put source code in `src/`, not in presentation or ideation folders.
- Keep decisions and research concise and dated in `group/ideation/`.
- Keep presentation assets and the final deck in `group/presentation/`.
- Do not commit `node_modules`, environment files, generated local-review output,
  or secrets.

## Agent setup

This repository ships its shared agent workflow:

- `$ponytail full` is the mandatory first step for every coding task.
- `$impeccable` follows for any UI-facing task.
- `AGENTS.md` is the binding order of operations for contributors and coding agents.

The skill sources and Impeccable hook are checked in under `.agents/` and
`.codex/`. After cloning, run the following once if your machine needs the
Impeccable native launcher:

```sh
npx impeccable install --providers=codex --project --yes
```

For the first product-design task, run `$impeccable init` and capture only
team-confirmed product context in `PRODUCT.md`.
