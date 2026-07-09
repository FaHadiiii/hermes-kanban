# Hermes Kanban — Dark Mode Spec (addendum to design-spec.md)

**Author:** Leha (Designer) · **Audience:** Jusoh (impl), Zali (review)
**Principle:** Invert the "Technical Minimalism" light language — flat warm-near-black canvas, hairline
borders, ONE accent (#FF5A1F). Do NOT borrow the textured-glass dark analytics look. Dark mode is a
flat instrument panel, same as light, just inverted.

---

## 1. Dark theme token block

Drop both blocks verbatim into the existing CSS (after the `:root` light tokens). The first is the
explicit `[data-theme="dark"]` override (user clicked toggle / stored preference). The second makes
OS `prefers-color-scheme: dark` the *default* when no explicit choice is stored.

```css
/* ===== Explicit dark (user toggled / persisted) ===== */
[data-theme="dark"]{
  --bg-base:#141312;
  --bg-panel:#1F1D1A;
  --bg-muted:#26231F;
  --border:#2E2B27;
  --text-1:#EDEAE4;
  --text-2:#A8A39B;
  --text-3:#7E7971;          /* tertiary/placeholder only — see risk #1 */
  --accent:#FF5A1F;          /* kept, NOT brightened — see note below */
  --accent-hover:#E64A15;
  --success:#16A34A;
  --warning:#B45309;         /* pill-only in dark — see risk #3 */
  --danger:#DC2626;          /* pill-only in dark — see risk #3 */

  /* Dark pill variants (low-sat pastel bg → dark-tinted bg + light legible fg) */
  --pill-neutral-bg:#26231F;  --pill-neutral-fg:#A8A39B;
  --pill-warning-bg:#2E2410;  --pill-warning-fg:#F5C264;
  --pill-accent-bg:#2A1A12;   --pill-accent-fg:#FF8A5C;
  --pill-danger-bg:#2A1414;   --pill-danger-fg:#F4A0A0;
  --pill-success-bg:#14261A;  --pill-success-fg:#7FE0A4;
}

/* ===== OS preference is the default when user hasn't chosen ===== */
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg-base:#141312;
    --bg-panel:#1F1D1A;
    --bg-muted:#26231F;
    --border:#2E2B27;
    --text-1:#EDEAE4;
    --text-2:#A8A39B;
    --text-3:#7E7971;
    --accent:#FF5A1F;
    --accent-hover:#E64A15;
    --success:#16A34A;
    --warning:#B45309;
    --danger:#DC2626;
    --pill-neutral-bg:#26231F;  --pill-neutral-fg:#A8A39B;
    --pill-warning-bg:#2E2410;  --pill-warning-fg:#F5C264;
    --pill-accent-bg:#2A1A12;   --pill-accent-fg:#FF8A5C;
    --pill-danger-bg:#2A1414;   --pill-danger-fg:#F4A0A0;
    --pill-success-bg:#14261A;  --pill-success-fg:#7FE0A4;
  }
}
```

**Pill class wiring (map existing light classes to dark tokens, no new markup):**
```css
[data-theme="dark"] .pill-neutral{background:var(--pill-neutral-bg);color:var(--pill-neutral-fg);}
[data-theme="dark"] .pill-warning{background:var(--pill-warning-bg);color:var(--pill-warning-fg);}
[data-theme="dark"] .pill-accent {background:var(--pill-accent-bg); color:var(--pill-accent-fg);}
[data-theme="dark"] .pill-danger {background:var(--pill-danger-bg); color:var(--pill-danger-fg);}
[data-theme="dark"] .pill-success{background:var(--pill-success-bg);color:var(--pill-success-fg);}
```
(Repeat the same 5 lines inside the `@media` block, or just rely on `[data-theme="dark"]` + the
media block both setting the `--pill-*` vars — the token override alone is enough if the light
`.pill-*` rules already read from CSS vars. If the light pills hardcode `#FEF3C7` etc., add the 5 lines above to BOTH blocks.)

**Grid note:** the body blueprint grid is built from `linear-gradient` using `--border`. With
`--border:#2E2B27` it becomes a near-invisible dark-on-dark hairline — consistent with the "faint"
intent. If Zali wants more presence on dark, add a dedicated `--grid-line:rgba(255,255,255,0.05)`
token and point the grid at it; otherwise no change needed.

### Accent decision (justification)
Keep `--accent:#FF5A1F` unchanged. As text/link/dot on the `#141312` canvas it already clears AA at
**~5.95:1**, so no brightening is required. Brightening to `#FF6B3D` would introduce a *second* accent
value, which the design system forbids ("one accent color"). The only sub-AA use of accent is
white-text-on-solid-accent (the active filter chip) — and that ratio (~3.1:1) is identical in light
mode, so we preserve parity rather than special-case dark.

---

## 2. Theme toggle button spec

**Placement:** topbar right cluster, between `LIVE` and the `refresh` chip:
`[ ● LIVE ]  [ THEME ☾ ]  [ ↻ refresh ]`

**Element:** `<button id="theme-toggle" class="chip" type="button" aria-label="Toggle color theme">`
Reuse the existing mono `.chip` style (hairline border, `bg-panel`/`bg-muted` fill, `rounded-sm`,
JetBrains Mono, `0.6875rem`, uppercase, `+0.08em` tracking) so it matches `refresh`.

**Label / icon:** static mono text `THEME` + a glyph span `.ico`. The glyph auto-flips with the
active theme via pure CSS (keeps the JS tiny — no label rewriting in script):
```css
.theme-toggle .ico::before{content:"☀";}                 /* sun = currently light */
[data-theme="dark"] .theme-toggle .ico::before{content:"☾";} /* moon = currently dark */
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]) .theme-toggle .ico::before{content:"☾";}
}
```

**Interaction (exact, Jusoh implement verbatim):**
- On click: flip `document.documentElement.dataset.theme` between `'light'`/`'dark'`, persist to
  `localStorage` key `kanban-theme`.
- On load: the inline script reads `localStorage('kanban-theme')`, falling back to
  `matchMedia('(prefers-color-scheme: dark)')`. No DB / user-derived values are interpolated into
  the script — it is fully static, so Caddy can whitelist its exact sha256 in
  `script-src 'sha256-...'` (everything else stays `'none'`).

**Exact inline script to whitelist** (minified, 307 chars — hash THIS exact string):
```js
const d=document.documentElement;const s=localStorage.getItem('kanban-theme');d.dataset.theme=s||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');document.getElementById('theme-toggle').onclick=()=>{const n=d.dataset.theme==='dark'?'light':'dark';d.dataset.theme=n;localStorage.setItem('kanban-theme',n)};
```
> On-load core (first 159 chars, through setting `theme`) is the critical part; the remaining ~148
> chars attach the click handler. CSP must hash the **complete 307-char** string. Put it in one
> `<script>` in `<head>` (no `src`, no attributes) so it runs before paint and avoids a flash.

To generate the hash: `echo -n '<script body above>' | openssl dgst -sha256 -binary | openssl base64`
then add `script-src 'sha256-<output>'` to the Caddy CSP.

---

## 3. Contrast / legibility risks for Zali (reviewer)

1. **`--text-3:#7E7971` is ~4.1:1 on `--bg-base`** — below AA (4.5). Intentional: it is
   tertiary/placeholder only (grid labels, `— EMPTY —`, mono timestamps). If you want strict AA
   everywhere, bump to `#8A857C` (~4.6:1) at the cost of flatter hierarchy. Flagged, not fixed.
2. **Active filter chip = white text on solid `--accent` (#FF5A1F) ≈ 3.1:1** — fails AA. This is
   *identical* to light mode (parity, not regression). Acceptable only if the chip label is
   ≥18.66px bold or ≥24px regular (large-text AA = 3:1). Verify the chip text size; otherwise
   switch its fill to a dark tint with `#FF8A5C` fg like the running pill.
3. **Bare `--warning` (#B45309) and `--danger` (#DC2626) as text on `--bg-panel` fail AA**
   (~3.3:1 / ~3.5:1). They are ONLY used inside pills now (dark-tinted bg + light fg, all ≥7:1).
   Do not use these tokens as standalone text on dark panels. Confirm no bare warning/danger text
   exists outside pills.
4. **`--accent-hover:#E64A15`** is slightly darker than accent; used only for hover/press states of
   the live dot / links — fine, no text-on-accent concern.
5. **Grid visibility on dark** is intentionally very low (dark hairline). Aesthetic only; if it
   reads as "broken" on dark, introduce `--grid-line` (risk-free, see Grid note §1).
6. **No flash of wrong theme (FOUC):** script must run in `<head>` before first paint. If placed at
   end of `<body>`, users on dark OS preference will see a light flash. Enforce head placement.
