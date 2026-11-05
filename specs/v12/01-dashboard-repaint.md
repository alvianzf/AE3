# 01 · Dashboard visual system repaint

Scope: the three authenticated portals — `(admin)`, `(practitioner)`, `(client)`.
Public routes (`(public)`) are **out of scope** and must not change.

## Problem

The private routes currently read as stale: frosted-glass panels with blur and
sheens, square-cornered divider rows, an icon rail with animated falling leaves
and a colored gradient wash, underline-only inputs, and a warm beige backdrop
with radial color blobs. It is busy, low-contrast, and dated (2021 glassmorphism).

## Direction

Calm, dense, professional "modern SaaS" — think Linear / Stripe / Vercel
dashboards, kept in the brand's rose + sage palette.

| Aspect | Today | After |
|---|---|---|
| Backdrop | beige + radial blobs, fixed | flat cool-neutral `#f6f7f9` |
| Surfaces | translucent glass + `backdrop-filter` | solid white cards, 1px hairline, soft 2-layer shadow |
| Radius | 0 on panels, 10px on controls | 8px controls, 12px cards, 999px chips |
| Sidebar | 12rem dark rail, falling leaves, gradient wash | 15rem solid deep-slate sidebar, no animation, section-aware active pill, user chip at bottom |
| Page header | sticky glass toolbar | sticky white top bar, 1.25rem title, subtitle, actions slot, hairline bottom |
| Content width | full bleed | padded canvas, `max-width` 80rem for non-workspace pages |
| Inputs | underline only | boxed, 1px border, 3px accent focus ring (also `Select`, `TextField`) |
| Buttons | glossy gradient | flat solid, subtle shadow, clear hover/active/focus |
| Stat tiles | tinted boxes, lift on hover | white card, icon in tinted rounded square, large tabular figures |
| Chips | uppercase tracked | sentence case, tinted pill, 12px |
| Type | system stack, 650/750 weights | system UI stack with `Inter` first, tabular numbers, weights 500/600/700 |
| Motion | blur, lift, fade | 120–200ms color/shadow transitions only; reduced-motion respected |

## Per-portal identity

Same structure, a different accent so role is obvious at a glance (previously
only the rail indicator varied):

- Client — rose `#9c3f5a` (brand, unchanged)
- Practitioner — teal `#0f766e`
- Admin — indigo `#4f46e5`

Implemented by overriding `--accent`, `--accent-ink`, `--accent-soft`,
`--rail-indicator` on each portal's layout root.

## Implementation approach (low risk)

The design system is already centralized, so the repaint is token-driven rather
than a per-page rewrite:

1. **Scope.** Each private layout sets `data-surface="app"` on `<html>` while
   mounted (removed on destroy). All new tokens live under
   `html[data-surface='app']`, so public pages are byte-for-byte unaffected —
   including body-level elements outside the shell (command palette, toasts,
   dialogs).
2. **`app.css`.** Tokens + shell classes (`.app-shell`, `.pane-row`,
   `.list-pane`, `.detail-pane`, `.detail-head`, `.list-row`) restyled under the
   scope. Class names and DOM contracts are kept so no page markup breaks.
3. **`Rail.svelte`.** Restyled; props and nav behavior unchanged. Drops
   `LeafField`. Mobile (<760px) still collapses to a bottom bar.
4. **Shared components.** `Button`, `StatTile`, `Chip`, `Tabs`, `TextField`,
   `Select`, `EmptyState`, `DataTable`, `Dialog`, `Menu`, `Skeleton` restyled via
   tokens; props unchanged. Public pages that use them are kept visually
   identical by reading scoped tokens with the old values as fallbacks.
5. **Home pages.** Practitioner / admin / client home get a light markup pass
   (greeting header, stat grid, card sections).

## Non-goals

No routing, data, API, copy, or behavior changes. No dark mode (follow-up). No
new dependencies or web-font downloads.

## Acceptance

- `npm run check` has no new errors; `npm run build` succeeds.
- Public routes render identically (no `data-surface`).
- Every private route shows: solid surfaces, no `backdrop-filter`, no falling
  leaves, readable contrast ≥ WCAG AA for body text and controls, visible focus
  ring, working mobile bottom bar.
