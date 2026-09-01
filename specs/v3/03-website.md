# 03 · Website

See also [17 · Full-app redesign](17-full-app-redesign.md) for a PM/UX
walkthrough proposing fixes to the public site's shell inconsistency,
directory search, and coach-detail CTA hierarchy.

The public surface. No login required except to submit a practitioner
signup or a client signup — browsing the directory and viewing a coach's
profile is open to anyone.

## Pages

| Page | Route | Purpose |
|---|---|---|
| **About** | `/about` | What the clinic is, static content |
| **Practitioner signup** | `/join` | Form → creates a `pending` practitioner row ([04](04-admin-portal.md)) |
| **Practitioner directory** | `/directory` | Browsable/filterable list of `approved` practitioners |
| **Coach detail** | `/coach/{id}` | One practitioner's full profile + contact form |
| **Client signup** | `/signup` | Regular email/password signup ([06](06-client-portal.md)) |
| **Log in** | `/login` | One form for all three roles — role is resolved server-side, not chosen |
| **Account** | `/account` | Change password, works for whichever role is signed in ([08](08-api.md#any-authenticated-role)) |

Clean top-level routes, not the `static/public/...` directory layout —
`/static/` is mounted only for the pages' own assets. `GET /` redirects to
`/login`.

## Shared navigation conventions

Apply across every app (public, [practitioner](05-practitioner-portal.md),
[client](06-client-portal.md), [admin](04-admin-portal.md)), not just this
one — documented here since this is the doc that already describes page
structure.

- **Breadcrumbs** on any page one level or deeper into a section —
  `/admin/users` ("Admin / Users"), every `/practitioner/*` and
  `/client/*` page. Not shown on single-level pages (`/about`, `/login`,
  `/directory`, …), where a one-item trail would be noise rather than a
  navigation aid.
- **User menu.** Every topbar that has an authenticated session shows one
  trigger on the right, not separate "Account" and "Log out" controls —
  clicking it opens a small dropdown with both. The trigger is a circular
  avatar-style icon (a person glyph in a bordered circle) plus a small
  separate chevron, not styled as a rectangular button — it's meant to
  read as "your account," not as one more action among the nav's other
  buttons. `/account` itself is the one exception (a plain Log out
  button; an "Account" link on the account page would point at itself).
- **Logo → your own section**, not a generic home. Clicking the brand
  logo goes to `/admin` from any admin page, `/practitioner/profile` from
  any practitioner page, `/client/questionnaire` from any client page, and
  `/directory` from any public page — never `/`, which only redirects to
  `/login` and would otherwise bounce a signed-in user through an
  unnecessary hop.
- **Health/status readout** (admin's "Knowledge library / Clinic
  reachable, N sources · M passages") lives in a footer at the bottom of
  the page, not the topbar — it's ambient system status, not something
  that needs to compete with navigation for space at the top.

## Practitioner directory

Modeled partly on vibly.io's directory
(`https://vibly.io/insuliniq/directory/`) — a card grid, not a table:

Each card shows: photo, name, one-line description, specialties (tags),
languages spoken, years of experience, consultation price. Filters: specialty,
language. Only `approved` practitioners appear — `pending`, `rejected`, and
`suspended` are never rendered, regardless of what a direct URL to their
detail page might otherwise show (see below).

Practitioners with a Basic plan and practitioners with a Pro plan are listed
identically here. The plan governs what a practitioner can *do* in their own
portal ([05](05-practitioner-portal.md)); it has no visible effect on the
public directory or detail page.

## Coach detail page

Full profile (everything on the card, plus the longer bio) and a **contact
form**: name, email, message. Submitting it:

1. Writes a row to `contact_form_submissions` (core store, [02](02-data-model.md)).
2. Notifies the practitioner (email) that someone wants an initial call.
3. Counts toward that practitioner's stats in the admin portal ([04](04-admin-portal.md)).

This is a lead-capture form, not a booking system — there is no calendar, no
confirmed-slot flow. Deliberately out of scope per [01](01-overview.md).

A direct link to a non-`approved` practitioner's detail page 404s rather than
rendering a broken or half-populated profile.

## Practitioner signup

Name, email, password, bio, specialties, languages, years of experience,
consultation price, photo upload. On submit, the practitioner exists with
`status = pending` and is invisible everywhere public until an admin approves
them ([04](04-admin-portal.md)). No plan is chosen at signup — every new
practitioner starts on Basic; upgrading to Pro is a later, separate action
gated by Stripe checkout ([09](09-payments.md)).

## Analytics

Every directory listing render and every coach-detail-page render logs a
`profile_view_events` row (core store) keyed to the practitioner shown. This
is the only tracking on the public site for this version — no cross-session
identity, no marketing pixels.
