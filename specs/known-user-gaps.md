# Client-portal audit — gaps found walking the app as a patient

Date: 2026-09-16
Method: read-only walkthrough of the public marketing/discovery pages, signup/login,
and the full `(client)` portal, cross-referenced against the backend routes they call
(`app/main.py`, `app/wearables.py`). No code changed.

Ranked roughly by how much a real patient would be frustrated or misled.

---

## 1. Practitioner sessions are practitioner-only — CONFIRMED INTENTIONAL, not a gap

Raised originally as a possible gap: a client can never see what their practitioner
discussed or decided (`/api/me/consult`, `/api/me/clients/{id}/sessions*` in
`app/main.py:1488-1862` are all practitioner-scoped, no client-side page surfaces any
of it). Confirmed with the product owner (2026-09-16): this is deliberate — clinical
sessions stay practitioner-only. No change made.

## 2. Wearables page never disclosed that connected data is fixture, not real — FIXED (2026-09-16)

`app/wearables.py`'s own module docstring states plainly: the OAuth connect flow is
real, but "what happens *after* a successful connection is deliberately fixture data,
not a live pull of the client's metrics." The client-facing page previously showed a
plain `Connected` chip with no caveat, and the dashboard tile reported "N connected"
the same way it'd report real files uploaded — actively misleading, since the OAuth
flow made the connection feel end-to-end real.

Fix shipped: `web/src/routes/(client)/client/wearables/+page.svelte` now shows a
"Coming soon" state instead of the connect flow (no OAuth buttons offered to clients),
and the dashboard tile (`.../dashboard/+page.svelte`) shows "Coming soon" instead of a
connection count. Backend OAuth plumbing (`app/wearables.py`) is untouched — this is a
client-UI-only change; the connect endpoints still exist for whenever the real
per-vendor data pull ships.

## 3. Health-record entry kinds are unexplained jargon for a non-clinical user — MEDIUM

`web/src/routes/(client)/client/record/+page.svelte` offers a `<Select>` of `lab`,
`condition`, `medication`, `note`, `history` (`KIND_LABELS`, lines 16-19) with a single
placeholder example ("Fasting glucose 92 mg/dL, 2026-09-14") and no other guidance. A
patient without clinical literacy won't reliably know whether "started taking
magnesium last week" belongs under `medication`, `note`, or `history`, and there's no
help text or example per category. Miscategorized entries are silent — nothing surfaces
this to the practitioner as ambiguous.

## 4. Questionnaire has no empty/attention state on the dashboard once answered — LOW-MEDIUM
The dashboard tile just flips from "Fill in" to "Submitted" (`dashboard/+page.svelte:14-18`)
with no indication of what happens next (reviewed? still pending?), consistent with gap #1 —
there's no feedback loop back from the practitioner side at all.

## 5. Practitioner directory quality gate is thin — MEDIUM
`/practitioners` (`(public)/practitioners/+page.svelte`) lists every approved
practitioner regardless of specialty match quality or plan; `/coach/[id]` shows bio/
years/languages but no reviews, ratings, or any third-party signal a real patient would
normally use to choose a healthcare provider. Reasonable for an early-stage product, but
worth naming as a real gap if patient acquisition (not just practitioner-side features)
is a near-term priority.

## 6. Signup pro-only filtering can silently drop a client's chosen practitioner — LOW
Already partially handled (`(public)/signup/+page.svelte:36-45` does surface
"isn't currently accepting new clients" when the preselected practitioner falls off the
pro-only list) — noting only because the underlying asymmetry (all practitioners
browsable on `/practitioners`, only `plan === 'pro'` signable-up-with) is easy to
reintroduce as a bug if that filter or its warning is ever touched. Not an active gap
today.

## 7. Files page: no file-type/size validation feedback before upload starts — LOW
`(client)/client/files/+page.svelte` accepts any file, relies entirely on the backend's
200 MB chunked-upload endpoint to reject oversized/invalid files after the transfer
begins — no client-side pre-check or type restriction, so a patient could wait through
a multi-minute upload before learning it's rejected. Low priority since chunked upload
already handles the mechanics; this is purely a "how long before you find out it
failed" UX gap.

---

## Explicitly NOT gaps (checked and ruled out)
- **Login/signup error handling** (`(public)/login`, `(public)/signup`,
  `POST /api/clients` in `app/main.py:1067-1097`): coherent. Wrong password → "Incorrect
  email or password." Re-signup on an existing email with a password already set → 409
  with a clear message and a login link. Practitioner-invited-but-not-yet-activated
  clients correctly complete signup by setting their password rather than erroring.
- **Contact-form dead end**: fixed already — 404s if the practitioner was
  suspended/rejected since the page was prerendered (`app/main.py:1046-1057`), rather
  than silently accepting a submission to nobody.
- **Health record privacy scoping**: correctly implemented — `GET /api/me/entries`
  filters out anything the practitioner wrote, and the client-side copy accurately
  states "you can only remove what you added yourself."
