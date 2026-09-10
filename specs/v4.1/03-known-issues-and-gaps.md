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

---

## Critical

### CR1 — Logout doesn't log out

`AppRail.svelte:30-33`'s sign-out control is a `<form method="post"
action="/api/auth/logout">`, but `onsubmit={(e) => e.preventDefault()}`
unconditionally cancels the submit — `/api/auth/logout` is never called.
Clicking "sign out" just client-side-navigates to `/login` while the
session cookie is presumably still valid server-side. Shared code, so this
affects all three authenticated portals identically. On a shared or public
machine this is a real access-control gap, not just a UX papercut: the
next person to open the app in that browser is still logged in as the
previous user.

### CR2 — The practitioner onboarding checklist can never show "not done"

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

### CR3 — A saved consult summary disappears on reload

`(practitioner)/practitioner/clients/[id]/+page.svelte:17-30`'s
`summarize()` writes the AI-generated summary into local component state
keyed by session id and shows a toast claiming it's "saved to the client
record" — but the page's loader never surfaces previously-saved summaries
on a fresh load, so reloading the page (or revisiting the client later)
shows no summary even though the backend presumably has it. A practitioner
has no way to read a summary they generated in an earlier session; the
toast's claim of persistence is not something the UI itself can verify.

---

## High

### H1 — Landing page and practitioner directory are the same route

Covered in full in [01](01-landing-and-directory-split.md). A cold visitor
to `/` gets a search UI with no product information; the actual pitch is
stranded on `/about`, one nav level away.

### H2 — User types are visually indistinguishable

Covered in full in [02](02-user-type-separation.md). Admin, practitioner,
and client portals share one shell with no visible role signal.

### H3 — Browsing a practitioner and signing up with one are disconnected flows

`coach/[id]/+page.svelte:54-60` has no "sign up with this practitioner"
action; a visitor has to separately reach `/signup` and re-pick the same
person from a bare `<select>` (`signup/+page.svelte:60-65`), losing all
context. Compounded by `signup/+page.svelte:26` silently filtering to
pro-plan practitioners only, with no equivalent filter on the
browse/directory grid — a practitioner a visitor found and liked can
vanish from signup with zero explanation. Full fix in
[01](01-landing-and-directory-split.md#fixing-the-handoff-this-split-would-otherwise-leave-broken).

### H4 — The practitioner's own knowledge screen has no search, filter, or pagination

`(practitioner)/practitioner/knowledge/+page.svelte:22-37` renders every
library source as an unbounded table of trust-weight sliders — no search,
category filter, or pagination, unlike the admin Library it mirrors
(paginated at 12/page as of a recent commit). A practitioner also can't
preview what a source actually says before weighting it — only
`title` + `grade` + a bare number input are shown, versus the admin
Library's in-modal document preview. As the library grows this screen
degrades faster than the one it's derived from.

### H5 — No path from a contact submission to a client record

`(practitioner)/practitioner/contacts/+page.svelte:36-38` lets a
practitioner mark a message "handled," but there's no button to convert it
into a client (`clients/+page.svelte`'s "Add client" dialog requires
manually retyping the name/email the contact already provided) and no
reply affordance (no `mailto:` link, no reply field). A fully manual,
error-prone bridge between two adjacent screens for what's presumably a
core conversion path (public contact → signed-up client).

### H6 — Creating a questionnaire silently deactivates the live one

`(admin)/admin/questionnaires/+page.svelte:14-19,96` — only one
questionnaire can be active; creating a new one immediately deactivates
whatever clients are currently answering. This is disclosed only inside
the *Edit* dialog's hint text (line 96); the *Create* flow
(`openCreate`, lines 25-30) gives no warning before an admin accidentally
replaces a live questionnaire.

### H7 — Practitioner plan changes have no confirmation; suspend/reject do

`(admin)/admin/users/+page.svelte:94-97,155` fires `setPlan` on every
`onchange` of a bare native `<select>` with zero confirmation, despite the
same file's own comment (lines 27-32) noting Suspend/Reject were
specifically upgraded to a shared confirm dialog for being "equally
consequential" — a billing-relevant plan change got no equivalent
protection against a misclick.

---

## Medium

### M1 — Client dashboard gives every task equal visual weight

`(client)/client/dashboard/+page.svelte:12-31` renders three `StatTile`s
(Questionnaire, Files, Wearables) at identical weight regardless of actual
urgency — a brand-new client with an unfilled questionnaire and zero
files/wearables sees three equally-quiet tiles, nothing marking which one
is actually blocking. [v4/03](../v4/03-visual-redesign.md) applied exactly
this kind of prioritization to the practitioner dashboard's checklist; no
equivalent exists on the client side, despite a first-time client
plausibly needing it more (a lay person handed a login, vs. a paid
professional onboarding into a work tool).

### M2 — No onboarding checklist anywhere in the client portal

Related to M1: `specs/v4/03`'s consolidated welcome+checklist pattern
exists for practitioners only. Nothing orients a first-time client toward
what to do first across questionnaire/files/wearables.

### M3 — Wearables feels like an unfinished feature bolted onto the portal

`(client)/client/wearables/+page.svelte:10,65` hardcodes three lowercase
provider strings (`oura`, `whoop`, `garmin`) styled via
`text-transform: capitalize` rather than real brand treatment, and nothing
on the page explains why a client would connect a wearable — what a
practitioner does with the data, why it matters. Connecting one
(`wearables/+page.svelte:17-24`) redirects off-app immediately with no
explanation shown first of what's about to happen.

### M4 — Client portal shares the exact component vocabulary of the clinical/admin tools, with no simplification for a lay audience

`Chip`, `Spotlight`, `DataTable`, `Button variant="outlined"/"text"` are
the same components used in the admin Library and practitioner consult
screens. `files/+page.svelte:57-68` renders a raw `media_type` (MIME type
string) as a table column — mildly technical surface for what's likely
the least technical of the three user types.

### M5 — Admin dashboard and the (frozen) Library page are two disconnected "home" screens

`/admin` (Library) is the landing route; `/admin/dashboard`
(`dashboard/+page.svelte:10-11`, "Site stats") is a second, separate home
with no link between them in either direction, and no stated reason
dashboard isn't the landing page instead of a secondary nav item.

### M6 — Admin stat tiles are unlabeled pass-through of backend keys

`(admin)/admin/dashboard/+page.svelte:13-17` generates tiles from
`Object.entries(s)` with `key.replaceAll('_','_ ')` as the label —
whatever fields `/admin/stats` returns become UI text directly, with no
control over order, grouping, or priority. Renaming a backend field
silently relabels/reorders the dashboard.

### M7 — Failed loads and genuinely-empty states render identically, portal-wide

`(admin)/admin/dashboard/+page.ts:6`, `users/+page.ts:7-8`,
`questionnaires/+page.ts:6`, `audit/+page.ts:6`, and
`(client)/client/dashboard/+page.ts:8-13` all catch failed fetches to
empty arrays/objects with no distinct error state — a broken endpoint and
"there's genuinely nothing here yet" look the same everywhere outside the
frozen Library page.

### M8 — Client detail is read-only apart from AI summaries

`(practitioner)/practitioner/clients/[id]/+page.svelte:36-63` has no edit
for name/email/dob/country (set once at creation,
`clients/+page.svelte:67-78`), no way to remove a stray file, and no
practitioner-notes field.

### M9 — Removing a client uses a native `confirm()`, inconsistent with the rest of the app

`(practitioner)/practitioner/clients/+page.svelte:36` is the only
destructive action in the portal not using the app's own `Dialog`
component (used one screen away for "Add client") — unstyled, untestable,
visually foreign to everything around it.

### M10 — Admins tab is read-only with no explanation

`(admin)/admin/users/+page.svelte:78-124` — "Practitioners" and "Admins"
are tabs on one screen; Admins has no create/edit/remove anywhere in the
file, and the "New practitioner" button (line 82) is scoped only to the
Practitioners branch, so switching tabs makes the primary action silently
vanish. Reads as an unfinished tab rather than a deliberate read-only
view — if it's deliberate, the UI should say so.

### M11 — Audit trail has no cross-reference to the Users screen, and doesn't cover practitioner-side vault activity

`(admin)/admin/audit/+page.svelte:24` renders `actor` as plain text with
no link back to Users. Separately, line 16 states practitioner-side
patient-vault activity "is separate and isn't shown here," with no
unified view anywhere — unclear whether that's an intentional privacy
boundary or a real gap; worth a product decision either way.

### M12 — Upgrade page shows no pricing or feature comparison

`(practitioner)/practitioner/upgrade/+page.svelte` is a single plan tier
with no comparison table and no price shown until after clicking through
to an external Stripe-hosted page.

---

## Low

### L1 — Practitioner dashboard stats have no time window

`(practitioner)/practitioner/dashboard/+page.svelte:39-43`'s three
`StatTile`s (new contacts, unviewed intake, consults logged) are plain
counts with no "since you last checked" framing.

### L2 — Anthropic API key field has weak affordance for a hard prerequisite

`(practitioner)/practitioner/profile/+page.svelte:70-76` is a bare
password input with no format hint or "test key" action, for a field that
hard-blocks Consult if wrong or missing (per CR2 above, the dashboard
checklist won't even warn you).

### L3 — Consult's client picker is an unbounded plain list

`(practitioner)/practitioner/consult/+page.svelte:146-157` — no
search/filter, degrades as a practitioner's roster grows. Same pattern as
H4's knowledge-screen list.

### L4 — Audit endpoint breaks the `/admin/...` API prefix convention

`(admin)/admin/audit/+page.ts:6` fetches `/audit` while every sibling
screen uses `/admin/stats`, `/admin/practitioners`, `/admin/questionnaires`
— a route-layer inconsistency, not user-visible, worth cleaning up
opportunistically.

### L5 — Client dashboard has no skeleton/loading state

`(client)/client/dashboard/+page.ts` sets `ssr = false` with no loading
guard around `data.response`/`data.files`/`data.connections` while it
resolves — likely a flash of an empty dashboard on slower connections,
compounding M1's "unclear priorities" first impression.

### L6 — Join form's numeric defaults read as real data

`join/+page.svelte:14-15` defaults `years`/`price` to `'0'` with no
placeholder distinguishing "not set" from "actually zero"; same pattern as
`coach/[id]/+page.svelte:47`'s `years_experience ?? 0`. See
[01](01-landing-and-directory-split.md#minor-data-honesty-fixes-worth-carrying-along).
