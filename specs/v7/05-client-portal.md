# v7/05 — Client portal redesign

Covers `(client)/client/*`: Dashboard, Questionnaire, Health record,
Files, Wearables.

Not read page-by-page in this pass, same norm as `04`. Direction only.

## Priority and framing

This portal serves the least technically-sophisticated audience of
the three (a practitioner's client, not a practitioner or admin) —
"user-friendly, not confusing" matters more here than anywhere else in
the app. Known relevant history: `specs/v6.6`'s "act as a real user"
audit already found and fixed a real honesty gap on this exact
portal (the Wearables page implying live vendor data when it was
fixture data — replaced with an explicit "Coming soon" state). That
audit's underlying method — walk the portal as a first-time client
with zero context and note every point of confusion — is exactly the
right lens for this redesign pass too, and should be repeated fresh
rather than assumed still fully resolved.

## Specific priorities

- **Onboarding** (`06`) matters most here of all three portals — a
  client did not choose this software, their practitioner did; they
  arrive with zero investment in learning it. A first-run guided tour
  (or at minimum a clear "start here" empty state via `EmptyState.svelte`
  from `01`) on first login is higher-value here than the command
  palette, which assumes a power user this audience mostly isn't.
- **Command palette** (`06`) is lower priority for this portal
  specifically — 5 nav items, not the dozen-plus surface area the
  admin Library page alone has. Still worth including for consistency
  (one shared component across all three portals, per `01`), just not
  a page where its absence would be a real gap.
- **Questionnaire** and **Health record** are form-heavy — same inline-
  validation and progress-indicator treatment `02` proposes for the
  public site's `/join`/`/signup`, reused here via the same underlying
  `TextField.svelte` improvements so the fix lands once, not per-page.
- **Files**: confirm current empty/loading states before assuming a
  gap — needs its own read.

## What this does not change

No change to any client-facing privacy boundary (a client's own
record visibility rules, `specs/v6.5`) or backend route — presentation
and new client-side interaction layers only, same as every other
portal in this redesign.
