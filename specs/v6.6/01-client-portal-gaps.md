# v6.6/01 — Client-portal audit and fixes

**Status: implemented, live-verified in production.**

A read-only walkthrough of the whole client-facing (public marketing/
discovery pages, signup/login, and the full `(client)` portal) app as a
real patient would experience it, cross-referenced against the backend
routes each page calls. Findings written to `specs/known-user-gaps.md`
(kept as a living doc, not frozen inside this version folder, since
future audits will update it in place).

## Findings

1. **A client can never see what their practitioner discussed or
   decided about them.** Every consult/session/summary route
   (`/api/me/consult`, `/api/me/clients/{id}/sessions*`) is
   practitioner-only; no page under `(client)/` shows a session,
   answer, or summary ever happened. Questionnaires and health-record
   entries go in with no confirmation loop back. Left open — this may
   be a deliberate boundary (clinical notes staying practitioner-only
   is defensible), but there's no explicit product decision on record
   either way, and nothing in the UI tells a client to expect a
   separate follow-up. Not fixed this version; needs a product call
   first.
2. **Wearables page never disclosed that connected data is fixture,
   not real.** `app/wearables.py`'s own docstring says so, but the
   client UI showed a plain "Connected" chip and the dashboard reported
   "N connected" indistinguishably from a real integration — a patient
   who connected an Oura ring would reasonably believe their real sleep
   data now reached their practitioner. **Fixed**: the OAuth
   connect/disconnect flow was replaced with an honest "Coming soon"
   state on both the wearables page and the dashboard tile. Backend
   OAuth plumbing (`app/wearables.py`) is untouched — only the client
   UI stopped offering a connection that doesn't do anything real yet.
3. **Health-record entry kinds were unexplained jargon.** `lab` /
   `condition` / `medication` / `note` / `history` with a single
   placeholder example and no other guidance — not fixed this version.
4. **Questionnaire ignored its own typed schema.** The backend/client
   contract already supported `text`/`number`/`date`/`choice`/
   `multi_choice` with `options` and a `theme`, but the client
   questionnaire page rendered every question as a plain textarea.
   **Fixed**: type-aware inputs (pill buttons for choice/multi_choice,
   native typed inputs for number/date), theme grouping (heading only
   shown when more than one theme is present), an answered/total
   progress bar, and a "Save changes" relabel + note when a response
   already exists instead of silently re-showing what looks like a
   blank form.
5. **Practitioner directory has no reviews/ratings/third-party
   signal**, and **files page gives no pre-upload validation feedback**
   — both noted, not fixed this version (low priority, no evidence of
   real user friction yet).

Ruled out as non-gaps (checked and confirmed correct): login/signup
error handling, the suspended-practitioner contact-form 404, and
health-record privacy scoping (a client can only ever see/delete their
own self-reported entries, never a practitioner's).

## Verification

`npm run check` — 0 errors. Manually verified on production after
deploy: wearables page shows "Coming soon", dashboard tile matches,
questionnaire renders typed inputs and the progress bar correctly.
