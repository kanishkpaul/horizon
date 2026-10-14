# horizon

A local-first decision workstation. It helps a person compare alternatives under explicit
uncertainty, commit to a feasible near-term plan, and revise it from what actually happened.
Horizon borrows Hermes's quiet desktop dialect almost entirely and leaves the kawaii out.

| | |
|---|---|
| Default skin | **First light** (`first-light`): apricot `#F5A65B` highlights and violet `#8B7CF6` actions on deep indigo; burnt orange and indigo on cool paper in light |
| Glyph | ⌓ |
| Kawaii | **Off.** Decisions about a career or money are not the place |
| Mode | Follows the OS |
| Surfaces | `horizon` CLI (Rust), desktop app (Tauri 2, React, Vite) |
| Uses | `base.css`, `skins.css`, `components.css` wrapped as React components, `loader.js`, `rust/theme.rs`; optional `tailwind-theme.css` |

## Feel

- A calm instrument, like a good spreadsheet and a good notebook had a child. Dense, legible,
  no decoration.
- Assumptions are first-class. Anything that changes the recommendation is visible, editable,
  and labelled with where it came from.
- Uncertainty is drawn, not hidden. Every outcome is a range, never a single number.
- The model is optional and looks optional: its suggestions sit in a distinct, dismissable
  style and never change a case without the user accepting them.

## Layout

```
┌ cases ───────┬ case: "PhD or industry offer" ───────────────────┬ evidence ──────┐
│ ⌓ PhD vs job │ outcomes   constraints   paths   plan   review   │ ● offer letter │
│   lab move   │ ──────────────────────────────────────────────   │   observed     │
│   Q3 budget  │ path A  ▕▓▓▓▓▓▓░░░▏ 0.42–0.71  [ 3 assumptions ] │ ○ "funding is  │
│              │ path B  ▕▓▓▓▓░░░░░▏ 0.31–0.66  [ 5 assumptions ] │   likely"      │
│ + new case   │ path C  ▕▓▓▓▓▓▓▓▓░▏ 0.55–0.80  [ 2 assumptions ] │   claimed      │
│              │                                                  │                │
│              │ ▸ what would change this: funding < 60% → B      │                │
└──────────────┴──────────────────────────────────────────────────┴────────────────┘
 no model · 3 paths · 1,000 runs · review in 13 days
```

- **Sidebar: cases.** One per decision, with its review date as `.row__meta`.
- **Main: the case**, with a `.seg` for its stages (outcomes, constraints, paths, plan,
  review). These follow the product's loop in order.
- **Rail: evidence and assumptions**, tagged with provenance (see COLOR.md): observed, claimed,
  inferred, unavailable.

## Key screens

- **Paths.** One row per path: name, an interval bar (`--ui-fill-1` track, `--ui-accent` for
  the 50% interval, `--ui-warm` whisker to 90%), the range in mono with tabular figures, and an
  assumptions count. Sorted by the user, not by score. No path is called "best".
- **What would change this.** A short list of thresholds ("If funding falls below 60%, path B
  leads"). This is the centrepiece of the product; give it `--text-md` and room.
- **Plan.** A fourteen-day list of commitments with effort estimates. Feasibility warnings
  (`--ui-warn`) appear inline when capacity is exceeded.
- **Review.** Recorded effort and outcomes next to what was planned, then "Revise plan".
- **Simulation running.** `<curve-loader type="lissajous" label="Running 1,000 samples">` in
  the path rows being computed; the rest of the case stays usable.

## Project components

- `IntervalBar`: track, interval, whiskers, tick at the median. Draws to scale. Colours from
  tokens only so it works in both modes.
- `AssumptionChip`: `.badge--outline` with the provenance dot; click opens it in the rail.
- `ModelSuggestion`: a `.widget` with a `--ui-purple` hollow dot and "Suggested by qwen3-8b",
  with Accept / Dismiss below. Accepting writes a normal assumption with the model recorded as
  its source.
- Charts: use the semantic and accent tokens; a categorical palette of at most five hues for
  paths, starting with accent, primary, cyan, warm, purple.

## Terminal

Banner: HORIZON in apricot-to-violet. Label ` ⌓ horizon `. Spinner without faces: `⌓ ◠ ◡`,
verbs simulating, sampling, weighing, branching, comparing policies, checking evidence, revising.
Tool verbs: `simulate`, `sample`, `retrieve`, `compare`, `record`. For a long simulation,
`horizon sim --watch` is a ratatui view with the same interval bars in block characters.

## Words

Plain, careful, never prescriptive. "Path C has the highest median under your assumptions" not
"Path C is the best choice". Units always: hours per week, months, currency code.

## Don't

- Don't show a single "score" for a life path, or rank paths by default.
- Don't draw a point estimate without its interval.
- Don't let the model's suggestion look like the user's own data.
