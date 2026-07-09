---
version: alpha
name: Hermes Kanban — Light Preview
description: A light, technical-minimalist read-only preview of the ayo-agents Kanban board.
colors:
  bg-base: "#FAFAF9"
  bg-panel: "#FFFFFF"
  bg-muted: "#F2F1EE"
  border-hairline: "#E5E3DE"
  text-primary: "#18181B"
  text-secondary: "#6B6B6B"
  text-tertiary: "#A3A29D"
  accent: "#FF5A1F"
  accent-hover: "#E64A15"
  status-success: "#16A34A"
  status-warning: "#B45309"
  status-danger: "#DC2626"
  status-neutral-bg: "#F2F1EE"
  status-neutral-fg: "#6B6B6B"
typography:
  h1:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  h2:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 600
    lineHeight: 1.3
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
  label-caps:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: 600
    letterSpacing: "0.08em"
  data-mono:
    fontFamily: "JetBrains Mono"
    fontSize: 0.75rem
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: 6px
  md: 8px
  lg: 10px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
components:
  summary-bar:
    backgroundColor: "{colors.bg-panel}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: 16px
  stat-card:
    backgroundColor: "{colors.bg-base}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: 12px
  status-column:
    backgroundColor: "{colors.bg-panel}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: 16px
  task-card:
    backgroundColor: "{colors.bg-panel}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: 12px
  status-pill:
    backgroundColor: "{colors.status-neutral-bg}"
    textColor: "{colors.status-neutral-fg}"
    rounded: "{rounded.full}"
    padding: 4px
  status-pill-active:
    backgroundColor: "{colors.accent}"
    textColor: "#FFFFFF"
---

## Overview

A **light, read-only preview** of the active Hermes Kanban board `ayo-agents`. The goal is a quiet, instrument-panel feel: warm off-white canvas, hairline borders, one orange accent, and monospace reserved strictly for system data (IDs, statuses, counts). It lets the user see at a glance what the multi-agent team (ayo / leha / jusoh / zali) is working on across seven workflow states. Built on the "Technical Minimalism" dev-tool language; dashboard patterns (KPI stat cards, summary bar, status pills) are lifted from the analytics guide but inverted to **light mode** — no dark glass, no textured backdrop, no large radii.

## Colors

- **bg-base (#FAFAF9):** page canvas — warm off-white, never pure white, never dark.
- **bg-panel (#FFFFFF):** cards, columns, summary surfaces.
- **bg-muted (#F2F1EE):** subtle fills (neutral status pill, hover rows, empty column well).
- **border-hairline (#E5E3DE):** 1px borders, dividers, blueprint grid lines.
- **text-primary (#18181B):** headlines, card titles, counts. Near-black, not #000.
- **text-secondary (#6B6B6B):** supporting copy, assignee, captions.
- **text-tertiary (#A3A29D):** grid labels, placeholder counts in empty columns.
- **accent (#FF5A1F):** the single decorative hue — active status filter, "live" marker, the one highlighted sparkline bar, link/CTA. Target ~3–5% visual weight.
- **accent-hover (#E64A15):** pressed/hover state of accent.
- **Semantic status colors (success #16A34A / warning #B45309 / danger #DC2626):** the *only* permitted deviation from one-accent. Reserved strictly for status-pill semantics (done / scheduled·ready / blocked), rendered as low-saturation pastel fills — never used decoratively.

## Typography

- **Inter** (humanist sans) for all prose, titles, labels. Weight + size carry hierarchy.
- **JetBrains Mono** reserved for data/status only: task IDs (`T-142`), status tokens (`[ RUNNING ]`), counts (`07`), timestamps (`2026-07-09 14:22`). Always uppercase with +0.06–0.08em tracking when used as a system tag.
- Display/headline sizes are intentionally small (1.5rem max) — this is a utility panel, not a hero.

## Layout

- **Blueprint grid (optional):** full-bleed 1px grid in `--border-hairline` at ~25% opacity behind all content; faint `+` crosshair ticks at intersections for "precision" feel. Purely decorative, never central.
- **Centered container:** max-width 1280px; grid bleeds full-width beyond it.
- **Top → bottom rhythm:**
  1. **Header row** — board name `ayo-agents` (sans H1) + live status dot in accent + `⌘R` refresh affordance hint (mono).
  2. **Summary bar** — one stat card per status (7) + one per assignee (4) on a wrapping flex row. Each stat card: mono uppercase label (e.g. `RUNNING`) + large proportional count (Inter bold) + tiny mono delta/legend.
  3. **Status columns** — 7 columns (triage / todo / scheduled / ready / running / blocked / done) in a horizontally-scrollable flex row, gutter 16px. Column header: mono status token + count chip + hairline divider. Cards stack vertically inside, 12px gap.
  4. **Footer line** — mono caption: total tasks, last sync time, board id.
- **Spacing:** 8px baseline. Card padding 12–16px, section gap `lg` (24px), cross-section break `xl` (48px). Columns scroll horizontally on narrow viewports; no vertical gridlines.

## Elevation & Depth

- No large shadows. Depth comes from hairline border + 1–2px soft ambient shadow on the summary bar only. Columns/cards are flat with hairline borders. Hover = border darken to `--text-tertiary` + bg to `--bg-muted` (150ms ease). Respect `prefers-reduced-motion`.

## Shapes

- Small, consistent radii: `sm` (6px) on cards/pills/inputs, `md` (8px) on columns/summary bar, `lg` (10px) max. `full` reserved for status pills and the live dot. No fully-rounded containers except pills.

## Components

**Summary bar** — panel strip holding 11 stat cards (7 status + 4 assignee). Title row above: mono eyebrow `BOARD · ayo-agents`. Active status filter chip uses `status-pill-active` (accent fill, white text) — the only accent surface besides the live dot.

**Stat card** — `bg-base` fill, hairline border, 12px padding. Layout: mono uppercase label top-left, Inter bold count (28–32px) dominating, optional 4–6 bar mini-sparkline bottom (grey bars, current/active bar in accent). Delta line: mono percentage + muted caption.

**Status column** — `bg-panel` column, 240px min-width, 16px gap to siblings. Header: mono status token (`[ RUNNING ]`) + count chip (mono) + 1px divider. Body: stack of task cards. Empty column shows `bg-muted` well + tertiary mono `— EMPTY —`.

**Task card** — `bg-panel`, hairline border, 6px radius, 12px padding, left-aligned. Contents:
- Row 1: task **title** (Inter 600, `text-primary`) + status **pill** (right).
- Row 2: mono **ID** (`T-142`) (tertiary) + **assignee** avatar-initial chip (ayo/leha/jusoh/zali) (secondary).
- Row 3: mono **priority** (`P0`/`P1`/`P2`) + mono **created_at** (`2026-07-09 14:22`) (tertiary).

**Status pill** — `full` radius, pastel semantic fill + darker text. States:
- `triage` / `todo` → neutral (`status-neutral-bg` / `status-neutral-fg`).
- `scheduled` / `ready` → warning pastel (`#FEF3C7` bg / `#B45309` fg).
- `running` → accent-tinted (`#FFEDE6` bg / `#E64A15` fg) — the only accent-adjacent pill, signaling "live".
- `blocked` → danger pastel (`#FEE2E2` bg / `#DC2626` fg).
- `done` → success pastel (`#DCFCE7` bg / `#16A34A` fg).

**Icons (Lucide / Feather, 1.5px stroke, 16–18px, grey default):**
- Refresh: `rotate-cw` · Live dot: `circle` (accent) · Assignee: `user` · Priority: `signal` / `flag` · Created: `clock` · Board: `layout-dashboard` · Blocked: `alert-triangle` · Search/filter: `search`.

## Data Contract (fields required from board `ayo-agents`)

Each task object must expose:

| Field | Type | Example | Used in |
|---|---|---|---|
| `id` | string (mono) | `T-142` | card row 2 |
| `title` | string | `Wire up kanban webhook` | card row 1 |
| `assignee` | enum `ayo\|leha\|juso\|zali` | `leha` | card row 2, summary (per-assignee) |
| `status` | enum `triage\|todo\|scheduled\|ready\|running\|blocked\|done` | `running` | column grouping, pill, summary |
| `priority` | enum `P0\|P1\|P2\|P3` | `P1` | card row 3 |
| `created_at` | ISO-8601 datetime | `2026-07-09T14:22:00Z` | card row 3 (display `YYYY-MM-DD HH:MM`) |
| `updated_at` | ISO-8601 datetime | `2026-07-09T15:10:00Z` | optional footer "last sync" / freshness |
| `labels` | string[] | `["infra","web"]` | optional tiny mono tag row |

Board-level fields for the summary bar: `board_id` (`ayo-agents`), `total_tasks`, `per_status_counts` (map of status→int), `per_assignee_counts` (map of assignee→int), `last_synced_at`.

## Do's and Don'ts

- **Do** keep accent (#FF5A1F) to ~3–5% — active filter, live dot, running-pill tint, one sparkline bar.
- **Do** render all IDs, statuses, counts, and timestamps in JetBrains Mono, uppercase-tagged.
- **Do** use hairline borders + small radii (6–10px); flat cards, minimal shadow.
- **Do** ground the blueprint grid in real board vocabulary (status tokens at intersections optional).
- **Don't** introduce a second decorative hue — semantic status pastels are the only exception, and stay low-saturation.
- **Don't** use dark theme, glassmorphism, gradients, or large drop shadows (those belong to the dark analytics guide, not here).
- **Don't** fill columns edge-to-edge on mobile — scroll horizontally, keep 16px gutters.
