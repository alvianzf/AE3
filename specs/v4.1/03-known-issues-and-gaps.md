# 03 · Known issues and gaps

Produced from a role-by-role read of all four portals
(`web/src/routes/(public)`, `(client)`, `(practitioner)`, `(admin)`),
2026-09-10. Same caveat as [v4/04](../v4/04-known-issues.md): **code-read,
not live-confirmed** — every finding traces to a specific file:line and a
concrete failure scenario, not speculation, but hasn't been clicked
through in a running environment. The admin Library page
(`admin/+page.svelte`) is out of scope throughout, per
[README](README.md).

Severity tiers follow [v4/04](../v4/04-known-issues.md)'s bar: **Critical**
= a real functional defect (silently broken behavior, data that looks
saved but isn't), not a design-taste call. **High** = a broken or dead-end
workflow a real user hits in normal use. **Medium** = a genuine gap that
degrades the experience but has a workaround or affects a minority of
sessions. **Low** = polish-tier, worth doing, not urgent.

**Status, re-audited 2026-09-11** (code-read against the current repo,
same caveat as above — not live-clicked): all 3 Critical and 5 of 7 High
findings are fixed, most with an explicit `specs/v4.1/03 <id>` comment at
the fix site. 2 High, 11 of 12 Medium, and 5 of 6 Low remain open; 1 Low
is obsolete (the feature it was about no longer exists). This table's own
"spec only, not built" status in [specs/README.md](../README.md) was
stale as of this same audit — corrected there alongside this file.

---

## Critical

### CR1 — Logout doesn't log out — FIXED

`AppRail.svelte:30-33`'s sign-out control is a `<form method="post"
action="/api/auth/logout">`, but `onsubmit={(e) => e.preventDefault()}`
unconditionally cancels the submit — `/api/auth/logout` is never called.
Clicking "sign out" just client-side-navigates to `/login` while the
session cookie is presumably still valid server-side. Shared code, so this
affects all three authenticated portals identically. On a shared or public
machine this is a real access-control gap, not just a UX papercut: the
next person to open the app in that browser is still logged in as the
previous user.

**Fixed:** `AppRail.svelte`'s sign-out form now calls an async `logout()`
handler that `POST`s `/auth/logout` before navigating to `/login`.

### CR2 — The practitioner onboarding checklist can never show "not done" — FIXED

`(practitioner)/practitioner/dashboard/+page.svelte:9-13`'s checklist
step "Set your Anthropic key" uses done-condition
`(data.notifications.unviewed_intake ?? 0) >= 0`, which is `true` for any
non-negative number — including `0` — so it is **structurally always
true**, unrelated to whether a key is actually on file. The real flag
(`profile/+page.svelte:71`'s `p?.has_anthropic_key`) exists and is unused
here. Step 1, "Add your first client," is hardcoded `done: true` and never
checks `data.clients`. A brand-new practitioner sees a fully-checked
onboarding list before doing anything, then hits a 403 later in Consult
(gated on the key per `+layout.svelte:6-9`) with no visible link back to
why — the one piece of UI meant to prevent exactly that failure actively
tells them it's handled.

**Fixed:** both steps now derive from real data (`data.clients?.length > 0`,
`data.recentSessions?.length > 0`). Also now moot for the reason the
original bug describes: v4.2 retired the per-practitioner Anthropic-key
model for one shared server-side Nebius key, so the "Set your Anthropic
key" step this finding was about no longer exists at all.

### CR3 — A saved consult summary disappears on reload — FIXED

`(practitioner)/practitioner/clients/[id]/+page.svelte:17-30`'s
`summarize()` writes the AI-generated summary into local component state
keyed by session id and shows a toast claiming it's "saved to the client
record" — but the page's loader never surfaces previously-saved summaries
on a fresh load, so reloading the page (or revisiting the client later)
shows no summary even though the backend presumably has it. A practitioner
has no way to read a summary they generated in an earlier session; the
toast's claim of persistence is not something the UI itself can verify.

**Fixed:** `summaries` now seeds from `data.sessions[*].summary` (the
backend was already returning it; nothing re-read it on load) — a
previously-saved summary survives a reload.

---

## High

### H1 — Landing page and practitioner directory are the same route — FIXED

Covered in full in [01](01-landing-and-directory-split.md). A cold visitor
to `/` gets a search UI with no product information; the actual pitch is
stranded on `/about`, one nav level away.

**Fixed:** `/` is now a real landing page (pitch, pillars, two CTAs); the
directory moved to `/practitioners`.

### H2 — User types are visually indistinguishable — FIXED

Covered in full in [02](02-user-type-separation.md). Admin, practitioner,
and client portals share one shell with no visible role signal.

**Fixed:** `AppRail`'s nav rail now shows a `portal-label` (and matching
`aria-label`) naming which portal you're in.

### H3 — Browsing a practitioner and signing up with one are disconnected flows — FIXED

`coach/[id]/+page.svelte:54-60` has no "sign up with this practitioner"
action; a visitor has to separately reach `/signup` and re-pick the same
person from a bare `<select>` (`signup/+page.svelte:60-65`), losing all
context. Compounded by `signup/+page.svelte:26` silently filtering to
pro-plan practitioners only, with no equivalent filter on the
browse/directory grid — a practitioner a visitor found and liked can
vanish from signup with zero explanation. Full fix in
[01](01-landing-and-directory-split.md#fixing-the-handoff-this-split-would-otherwise-leave-broken).

**Fixed:** `coach/[id]` now links `/signup?practitioner={p.id}` directly.

### H4 — The practitioner's own knowledge screen has no search, filter, or pagination — FIXED

`(practitioner)/practitioner/knowledge/+page.svelte:22-37` renders every
library source as an unbounded table of trust-weight sliders — no search,
category filter, or pagination, unlike the admin Library it mirrors
(paginated at 12/page as of a recent commit). A practitioner also can't
preview what a source actually says before weighting it — only
`title` + `grade` + a bare number input are shown, versus the admin
Library's in-modal document preview. As the library grows this screen
degrades faster than the one it's derived from.

**Fixed:** a search input was added (title match); pagination brought in
line with the admin Library it mirrors, per the fix's own comment.
Source preview-before-weighting wasn't independently re-verified this
pass.

### H5 — No path from a contact submission to a client record — FIXED

`(practitioner)/practitioner/contacts/+page.svelte:36-38` lets a
practitioner mark a message "handled," but there's no button to convert it
into a client (`clients/+page.svelte`'s "Add client" dialog requires
manually retyping the name/email the contact already provided) and no
reply affordance (no `mailto:` link, no reply field). A fully manual,
error-prone bridge between two adjacent screens for what's presumably a
core conversion path (public contact → signed-up client).

**Fixed:** a "Convert to client" action now exists on the contacts screen
(per the fix's own comment referencing this finding).

### H6 — Creating a questionnaire silently deactivates the live one — STILL OPEN

`(admin)/admin/questionnaires/+page.svelte:14-19,96` — only one
questionnaire can be active; creating a new one immediately deactivates
whatever clients are currently answering. This is disclosed only inside
the *Edit* dialog's hint text (line 96); the *Create* flow
(`openCreate`, lines 25-30) gives no warning before an admin accidentally
replaces a live questionnaire.

**Still open, re-verified 2026-09-11:** `openCreate()` still just resets
form state and opens the dialog — no warning before an admin overwrites a
live questionnaire.

### H7 — Practitioner plan changes have no confirmation; suspend/reject do — STILL OPEN

`(admin)/admin/users/+page.svelte:94-97,155` fires `setPlan` on every
`onchange` of a bare native `<select>` with zero confirmation, despite the
same file's own comment (lines 27-32) noting Suspend/Reject were
specifically upgraded to a shared confirm dialog for being "equally
consequential" — a billing-relevant plan change got no equivalent
protection against a misclick.

**Still open, re-verified 2026-09-11:** the shared confirm `Dialog` this
file added (see [L3 in v4/04](../v4/04-known-issues.md#l3)) only covers
`'suspend' | 'reject'` — `setPlan` still fires directly from the
`<select>`'s `onchange` with no confirmation step.

---

## Medium

### M1 — Client dashboard gives every task equal visual weight — STILL OPEN

`(client)/client/dashboard/+page.svelte:12-31` renders three `StatTile`s
(Questionnaire, Files, Wearables) at identical weight regardless of actual
urgency — a brand-new client with an unfilled questionnaire and zero
files/wearables sees three equally-quiet tiles, nothing marking which one
is actually blocking. [v4/03](../v4/03-visual-redesign.md) applied exactly
this kind of prioritization to the practitioner dashboard's checklist; no
equivalent exists on the client side, despite a first-time client
plausibly needing it more (a lay person handed a login, vs. a paid
professional onboarding into a work tool).

**Still open, re-verified 2026-09-11:** no priority/urgency signal found
in this file.

### M2 — No onboarding checklist anywhere in the client portal — STILL OPEN

Related to M1: `specs/v4/03`'s consolidated welcome+checklist pattern
exists for practitioners only. Nothing orients a first-time client toward
what to do first across questionnaire/files/wearables.

**Still open, re-verified 2026-09-11.**

### M3 — Wearables feels like an unfinished feature bolted onto the portal — STILL OPEN

`(client)/client/wearables/+page.svelte:10,65` hardcodes three lowercase
provider strings (`oura`, `whoop`, `garmin`) styled via
`text-transform: capitalize` rather than real brand treatment, and nothing
on the page explains why a client would connect a wearable — what a
practitioner does with the data, why it matters. Connecting one
(`wearables/+page.svelte:17-24`) redirects off-app immediately with no
explanation shown first of what's about to happen.

**Still open, re-verified 2026-09-11:** provider list is still the same
three lowercase strings; no explanatory copy found.

### M4 — Client portal shares the exact component vocabulary of the clinical/admin tools, with no simplification for a lay audience — STILL OPEN

`Chip`, `Spotlight`, `DataTable`, `Button variant="outlined"/"text"` are
the same components used in the admin Library and practitioner consult
screens. `files/+page.svelte:57-68` renders a raw `media_type` (MIME type
string) as a table column — mildly technical surface for what's likely
the least technical of the three user types.

**Still open, re-verified 2026-09-11:** `files/+page.svelte` still has a
`media_type` column rendering the raw value directly.

### M5 — Admin dashboard and the (frozen) Library page are two disconnected "home" screens — STILL OPEN

`/admin` (Library) is the landing route; `/admin/dashboard`
(`dashboard/+page.svelte:10-11`, "Site stats") is a second, separate home
with no link between them in either direction, and no stated reason
dashboard isn't the landing page instead of a secondary nav item.

**Still open, re-verified 2026-09-11:** no cross-link found either
direction.

### M6 — Admin stat tiles are unlabeled pass-through of backend keys — STILL OPEN

`(admin)/admin/dashboard/+page.svelte:13-17` generates tiles from
`Object.entries(s)` with `key.replaceAll('_','_ ')` as the label —
whatever fields `/admin/stats` returns become UI text directly, with no
control over order, grouping, or priority. Renaming a backend field
silently relabels/reorders the dashboard.

**Still open, re-verified 2026-09-11:** same `Object.entries(s)` +
`key.replaceAll('_', ' ')` pattern, unchanged.

### M7 — Failed loads and genuinely-empty states render identically, portal-wide — STILL OPEN

`(admin)/admin/dashboard/+page.ts:6`, `users/+page.ts:7-8`,
`questionnaires/+page.ts:6`, `audit/+page.ts:6`, and
`(client)/client/dashboard/+page.ts:8-13` all catch failed fetches to
empty arrays/objects with no distinct error state — a broken endpoint and
"there's genuinely nothing here yet" look the same everywhere outside the
frozen Library page.

**Still open, re-verified 2026-09-11:** `admin/dashboard/+page.ts` still
does `.catch(() => ({}))` with no distinct error state; other listed
loaders not individually re-checked this pass.

### M8 — Client detail is read-only apart from AI summaries — STILL OPEN

`(practitioner)/practitioner/clients/[id]/+page.svelte:36-63` has no edit
for name/email/dob/country (set once at creation,
`clients/+page.svelte:67-78`), no way to remove a stray file, and no
practitioner-notes field.

**Still open, re-verified 2026-09-11:** no edit affordance or notes field
found in this file.

### M9 — Removing a client uses a native `confirm()`, inconsistent with the rest of the app — FIXED

`(practitioner)/practitioner/clients/+page.svelte:36` is the only
destructive action in the portal not using the app's own `Dialog`
component (used one screen away for "Add client") — unstyled, untestable,
visually foreign to everything around it.

**Fixed:** now uses the shared `Dialog` component (per the fix's own
comment referencing this finding), matching "Add client" on the same
screen.

### M10 — Admins tab is read-only with no explanation — STILL OPEN

`(admin)/admin/users/+page.svelte:78-124` — "Practitioners" and "Admins"
are tabs on one screen; Admins has no create/edit/remove anywhere in the
file, and the "New practitioner" button (line 82) is scoped only to the
Practitioners branch, so switching tabs makes the primary action silently
vanish. Reads as an unfinished tab rather than a deliberate read-only
view — if it's deliberate, the UI should say so.

**Still open, re-verified 2026-09-11:** no admin create/edit control found
in this file; unclear whether this is deliberate — still worth a product
decision either way, per the original finding.

### M11 — Audit trail has no cross-reference to the Users screen, and doesn't cover practitioner-side vault activity — STILL OPEN

`(admin)/admin/audit/+page.svelte:24` renders `actor` as plain text with
no link back to Users. Separately, line 16 states practitioner-side
patient-vault activity "is separate and isn't shown here," with no
unified view anywhere — unclear whether that's an intentional privacy
boundary or a real gap; worth a product decision either way.

**Still open, re-verified 2026-09-11:** `actor` still renders as plain
text, no link.

### M12 — Upgrade page shows no pricing or feature comparison — STILL OPEN

`(practitioner)/practitioner/upgrade/+page.svelte` is a single plan tier
with no comparison table and no price shown until after clicking through
to an external Stripe-hosted page.

**Still open, re-verified 2026-09-11:** still just a Basic/Pro chip and an
"Upgrade to Pro" button — no price or comparison shown in-app.

---

## Low

### L1 — Practitioner dashboard stats have no time window — STILL OPEN

`(practitioner)/practitioner/dashboard/+page.svelte:39-43`'s three
`StatTile`s (new contacts, unviewed intake, consults logged) are plain
counts with no "since you last checked" framing.

**Still open, re-verified 2026-09-11.**

### L2 — Anthropic API key field has weak affordance for a hard prerequisite — OBSOLETE

`(practitioner)/practitioner/profile/+page.svelte:70-76` is a bare
password input with no format hint or "test key" action, for a field that
hard-blocks Consult if wrong or missing (per CR2 above, the dashboard
checklist won't even warn you).

**Obsolete:** v4.2 retired the per-practitioner Anthropic-key model
entirely for one shared server-side Nebius key — there's no longer a
practitioner-facing API key field for this finding to apply to.

### L3 — Consult's client picker is an unbounded plain list — STILL OPEN

`(practitioner)/practitioner/consult/+page.svelte:146-157` — no
search/filter, degrades as a practitioner's roster grows. Same pattern as
H4's knowledge-screen list.

**Still open, re-verified 2026-09-11:** no search/filter found on the
client picker itself (unlike H4's knowledge screen, which now has one).

### L4 — Audit endpoint breaks the `/admin/...` API prefix convention — STILL OPEN

`(admin)/admin/audit/+page.ts:6` fetches `/audit` while every sibling
screen uses `/admin/stats`, `/admin/practitioners`, `/admin/questionnaires`
— a route-layer inconsistency, not user-visible, worth cleaning up
opportunistically.

**Still open, re-verified 2026-09-11:** still fetches `/audit`, not
`/admin/audit`.

### L5 — Client dashboard has no skeleton/loading state — STILL OPEN

`(client)/client/dashboard/+page.ts` sets `ssr = false` with no loading
guard around `data.response`/`data.files`/`data.connections` while it
resolves — likely a flash of an empty dashboard on slower connections,
compounding M1's "unclear priorities" first impression.

**Still open, re-verified 2026-09-11:** `ssr = false` unchanged; no
skeleton/loading guard found.

### L6 — Join form's numeric defaults read as real data — STILL OPEN

`join/+page.svelte:14-15` defaults `years`/`price` to `'0'` with no
placeholder distinguishing "not set" from "actually zero"; same pattern as
`coach/[id]/+page.svelte:47`'s `years_experience ?? 0`. See
[01](01-landing-and-directory-split.md#minor-data-honesty-fixes-worth-carrying-along).

**Still open, re-verified 2026-09-11:** `years`/`price` still default to
`'0'`, no placeholder distinguishing unset from zero.
