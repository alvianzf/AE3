# v7/04 — Practitioner portal redesign

Covers `(practitioner)/practitioner/*`: Dashboard, Clients, Consult,
Contacts, Knowledge, Questionnaires, Profile, Upgrade.

Not read page-by-page in this pass (consistent with `01`'s and `03`'s
stated norm — each gets its own read-then-spec treatment when
scheduled, in the phase order `07` lays out). This file sets direction
and priority only.

## Consult — almost certainly the highest-value page to redesign first

Per `specs/v6.4`'s history, already rebuilt once into a "GPT/Claude-
style chat interface" (persistent sidebar, calendar-badge history, a
bottom-pinned composer, markdown rendering, a sources accordion) —
likely the portal's best-already-designed page, and also its most-used
one (a practitioner's actual daily work surface). Priorities here are
narrower than a rebuild:

- Apply `01`'s updated type/motion tokens to the existing structure.
- Loading state polish (`Skeleton.svelte`) for a streaming answer's
  first moments, if not already present — worth confirming against
  the real current implementation rather than assuming.
- Command-palette integration: jump to a specific client's thread
  without scrolling the sidebar list.

## Clients, Knowledge (library weights)

Knowledge in particular interacts directly with this week's admin-side
work (`v6.9`-`v6.11`: private documents, uploader, doc-type) but has
had none of the Icons/List/Table/view-mode/menu treatment the admin
Library page got — it's still the older `DataTable.svelte`-based list.
Whether to bring it up to the same interaction pattern as the admin
Library (shared components from `01` make this cheaper than it would
have been before this redesign) or keep it intentionally simpler
(a practitioner's own knowledge base is typically much smaller than
the shared library) is a real scope decision for whoever reviews this
spec, not assumed here.

## Dashboard, Contacts, Questionnaires, Profile, Upgrade

Flagged for individual read-then-spec passes. `Upgrade` in particular
is a conversion page (the free→Pro moment) and deserves the same
"friction costs real users" attention `02` gives `/join`/`/login`/
`/signup`.

## Cross-cutting

- Nav rail: same visual refresh as `03`'s admin section — one shared
  component, one pass covers all three portals' rails simultaneously
  once `01`'s tokens are in place.
- Onboarding (`06`): a first-run tour is highest-value here for a
  brand-new practitioner specifically on Consult (the core value
  prop) and the Pro-upgrade gates (several nav items already render
  `locked`/`Pro` — confirming a new practitioner understands *why*
  before they hit a paywall mid-task, not after).

## What this does not change

No change to any backend route, auth gate, or Pro/free permission
logic — purely presentation and new client-side interaction layers, as
stated in `00-overview.md`.
