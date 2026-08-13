# 03 · Website

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
