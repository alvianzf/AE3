# 04 · Known issues — PM/QA/Clinician review

Produced by a PM/QA/Clinician-lens review of the current build on
2026-09-09 — the deployed SvelteKit frontend (`web/`) and its FastAPI
backend (`app/`), covering all four portals plus the API/data layer.
Unlike [v2/13](../v2/13-known-issues.md), this pass is **code-confirmed
only, not live-confirmed**: this environment has no running Neo4j instance
and no real `ANTHROPIC_API_KEY`, so nothing here was reproduced by clicking
through the live app. Every finding traces to a specific file:line and a
concrete failure scenario reasoned from the actual code on both sides of
each contract (route handler + the frontend call site), not speculation —
but a small number could differ from true runtime behavior in ways static
reading can't catch. Treat this as a strong starting punch list, worth a
live-environment spot-check before triage, not as already-verified.

**Status: reporting only. Nothing below has been fixed in this pass** — the
instruction for this review was to find and record, not to build fixes.

**One process note before the findings:** this document lives in `v4/`
because `v4/` — the SvelteKit rewrite — is what's actually deployed
(commit `5e0c14f`, 2026-09-02). [`specs/README.md`](../README.md)'s table
and [`v4/README.md`](README.md) both still say v3 is "current" / "actually
built and deployed" and v4 is "proposed, not approved" — that's stale as of
the same commit and is itself worth fixing (formally cutting `v4/` per
`specs/README.md`'s own versioning rule), separately from anything below.

---

## Critical

Live security/access-control defects, or a flagship, user-visible feature
that is completely non-functional despite existing UI for it — the same bar
[v2/13](../v2/13-known-issues.md) used for its Critical tier.

### C1 — An unapproved or rejected practitioner gets full paid access — FIXED

`require_practitioner` and `require_pro_practitioner` (`app/auth.py:66-87`)
only ever check `status == "suspended"` — neither checks for `"pending"` or
`"rejected"`. `POST /api/me/upgrade` (`app/billing.py:78-84`) is guarded
only by `require_practitioner`, so an unapproved or explicitly rejected
applicant can pay via Stripe, get `plan="pro"`, and pass
`require_pro_practitioner` on every client/consult route
(`app/main.py:921-1270`) — adding real clients and running consults before,
or after being denied, admin review. This directly contradicts what the
applicant is told at
`web/src/routes/(public)/join/submitted/+page.svelte:12`: *"An admin will
review your application. You'll get access once approved."* No frontend
route restricts a pending practitioner's UI to a status-only view
(`web/src/routes/(practitioner)/practitioner/+layout.ts:6-18`); they land
on the full dashboard.

**Fixed:** `require_pro_practitioner` (`app/auth.py`) now also requires
`status == "approved"`, and `POST /api/me/upgrade` (`app/billing.py`) 403s
with a clear message before creating a Stripe checkout session unless the
practitioner is already approved. A pending/rejected practitioner can still
log in to see their own status (unchanged, intentional), but can no longer
pay for or use Pro features. The frontend status-only-view gap
(`+layout.ts`) is a separate, lower-stakes follow-up — not fixed in this
pass.

### C2 — The anti-hallucination verdict badge always shows the wrong state — FIXED

`consult/+page.svelte:98` checks `result.verdict === 'pass'`. The real SSE
`result` payload (`app/main.py:1086-1094`) has no top-level `verdict` — it's
`result.check.verdict`, and `check` can be `null` when `run_check=false`.
The pass/weak chip is therefore always `undefined`, always renders the
"warn" tone, and never reflects whether the Checker actually verified the
answer. This is the UI for the product's headline safety claim ("An
independent check guards each answer") and it cannot currently show a true
"pass."

**Fixed:** reads `result.check?.verdict`; shows a neutral "not
independently checked" chip when `check` is `null` (i.e. `run_check=false`)
instead of a false "warn." Also now surfaces `check.unsupported` (the
claims the Checker couldn't verify) when present.

### C3 — Citations are never rendered — the `[S1]`/`[S2]` markers are dead text — FIXED

`result.sources` — a rich per-passage array with `label`, `locator`,
`origin`, `snippet` (`app/main.py:1108-1126`) — is captured by
`streamConsult` (`consultStream.ts`) but never rendered anywhere in
`consult/+page.svelte`; only `result.answer` (line 101) is shown as a plain
`<p>`. The Specialist's inline `[S1]`/`[S2]` citation markers render as
inert literal text with nothing to click. This breaks README.md's core
grounding claim — "every citation carries a locator... click one to jump to
the passage" — which has no working UI in the current build.

**Fixed:** the answer text is now split on `[S1]`/`[S2]`… markers; each one
that matches a real entry in `result.sources` renders as a button that
scrolls to that source's card. A new sources panel renders every source's
label, title, locator, and snippet. [H10](#h10) (librarian reasoning, the
other half of this transparency gap) is fixed in the same change.

### C4 — A "weak"-verdict answer is summarized into the permanent patient record with no trace it was flagged — FIXED

`POST /api/me/clients/{id}/sessions/{id}/summary`
(`app/main.py:1207-1227`) builds the Summariser's input from
`vault.session_transcript()` (`app/vault.py:455-458`), which concatenates
only `question`+`answer` from `session_turns`. The Checker's verdict and
unsupported-claims list live in the same row's `payload` column
(`app/main.py:1128-1131`) but `session_transcript()` never reads it. An
answer the system itself flagged as containing an unsupported clinical
claim gets written into the patient's permanent record indistinguishably
from a fully-verified one.

**Fixed:** `session_transcript()` now reads each turn's stored `payload`
and inlines a `[Internal accuracy check flagged this answer as '<verdict>':
...]` note next to any turn that wasn't a clean `pass`, so the Summariser
sees it. A new `session_has_flagged_turn()` also appends a deterministic
warning line to the stored summary itself whenever any turn was flagged —
not left to the Summariser's discretion to mention it.

### C5 — A practitioner's own down-weighted source can still reach the answer — FIXED

`me_consult` (`app/main.py:996-1003`) applies a practitioner's personal
source weight override before filtering the Librarian's catalogue, but
`knowledge.traverse()`'s `adjacent`/`linked` hops
(`app/knowledge.py:610-635`) filter newly-discovered passages against the
raw shared `min_grade` int, not the practitioner's weight. A source a
practitioner has explicitly down-weighted below their own threshold can
still surface in an answer if it's linked by shared concepts to a source
that was opened — silently breaking README.md's "you control the
knowledge" promise for exactly the traversal machinery it's meant to
govern.

**Fixed:** `traverse()` now takes an optional `weights` map and re-checks
every gathered passage's *effective* grade (the practitioner's override if
one exists, else the source's shared grade) against `min_grade` after all
four hops run, not just at the Cypher-query level. `me_consult` now passes
the same `weights` dict it already computed for the catalogue.

### C6 — Self-serve client signup always fails — the site's primary conversion path cannot be completed — FIXED

`web/src/routes/(public)/signup/+page.svelte:19` posts
`{name, email, password}` with no `practitioner_id`.
`client_signup` (`app/main.py:560-589`) 400s ("practitioner_id is required
for a new client") without one, and no public page — not `/signup`, not
`coach/[id]` — ever collects or passes one. Every visitor who clicks "Get
started" and fills the signup form gets a confusing, unfixable 400. Same
class of bug as [v2/13 H1](../v2/13-known-issues.md#h1), which was fixed
once already (a practitioner-picker was added to `/signup`) — that fix
did not carry forward into the rewrite.

**Fixed:** `/signup` now fetches `GET /api/practitioners` client-side on
mount (not at prerender time, so the list can't go stale the way a
build-time snapshot could — see [02](02-open-questions.md)'s prerendering
risk), filters to `plan === 'pro'` (only Pro practitioners can accept
clients, same rule `coach/[id]`'s contact flow already respects), and
requires a selection before submit is enabled. An explicit empty state
covers the case where no Pro practitioner exists yet.

### C7 — Unauthenticated photo upload has no validation and is served without XSS hardening — FIXED

`practitioner_signup` (`app/main.py:515-536`, no auth required) accepts any
`photo` file; `_save_photo` (`app/main.py:470-474`) writes the raw bytes
under the client-supplied filename's extension with no size cap, no
content-type allowlist, no magic-byte check. `join/+page.svelte:67`'s
`accept="image/*"` is client-side only. `/photos` is a raw `StaticFiles`
mount (`app/main.py:1335`) with no `X-Content-Type-Options: nosniff` —
unlike `/api/sources/{id}/original`, which explicitly restricts inline
rendering to pdf/text and sets `nosniff` for exactly this reason
(`app/main.py:393-403`). An `.svg` or `.html` "photo" is a stored-XSS
vector on the public, pre-auth signup path.

**Fixed:** `_save_photo` now sniffs real magic bytes (JPEG/PNG/GIF/WebP
only, no PIL dependency needed) and saves under the *detected* extension,
not whatever the client claims — an `.svg`/`.html` upload 400s outright
regardless of its filename or declared content-type. Added a 5 MB cap. A
new middleware sets `X-Content-Type-Options: nosniff` on every `/photos/*`
response, same as `/original` already does.

### C8 — Switching clients mid-consult can attribute one patient's AI answer to another, with no label showing whose answer it is — FIXED

During `asking = true`, neither the client-list buttons
(`consult/+page.svelte:63`) nor the client `Select` (line 74 —
`Select.svelte` has no `disabled` prop at all) are locked. Switching to a
different client while a previous question is still streaming lets a stale
answer for client A render right after switching to client B — and the
result block (`consult/+page.svelte:95-103`) never displays which client
the shown answer is for, so the mix-up is invisible to the practitioner. In
a clinical tool, an answer silently rendered against the wrong patient
context is a safety issue, not a cosmetic one.

**Fixed:** `Select` gained a `disabled` prop; both the client list buttons
and the Select are disabled while `asking`, so `clientId` structurally
cannot change during a request — no separate "which client was this
answer for" tracking needed. Superseded by [H4](#h4)'s conversation-thread
rewrite: switching clients now always clears the whole thread and starts a
new session, rather than a single result being at risk of mislabeling.

### C9 — A demoted superadmin keeps superadmin power for up to 12 hours — FIXED

`require_superadmin` (`app/auth.py:60-63`) checks
`session.get("admin_role")` — the cookie's cached claim from login time —
not a fresh DB read. `require_admin` re-checks `is_active` live
specifically to close this class of bug (its own comment says so), but the
same fix was never applied to the role field. `superadmin_set_admin_role`
(`app/main.py:621-630`) can demote another admin, but that admin's existing
session cookie still grants superadmin routes until it expires
(`_MAX_AGE` = 12h). Same shape of bug as
[v2/13 C1](../v2/13-known-issues.md#c1) (suspension not enforced live),
recurring on a different field.

**Fixed:** `require_superadmin` now fetches the admin's live DB row and
checks `admin["role"]`, the same pattern `require_admin` already uses for
`is_active`. A demotion now takes effect on the demoted admin's very next
request, not after their cookie expires.

---

## High

Major promised features that are either half-built with no UI, or built and
then regressed from a previous version.

### H1 — The admin library has no delete or regrade UI — a regression — FIXED

`PATCH /api/sources/{id}` (regrade) and `DELETE /api/sources/{id}`
(`app/main.py:411`, `422`) both still exist, and the pre-rewrite admin page
used both — a grade slider plus a two-step delete confirmation warning
"Answers will stop citing it" (`static/app.js:330-369`). The current
`web/src/routes/(admin)/admin/+page.svelte` (including this review's own
recent library redesign) has neither: once ingested, a source's grade can
never be changed and it can never be removed, through any UI. README.md's
"What it demonstrates" table lists "A source can be corrected or removed"
as a core, demoed capability.

**Fixed:** the library table's grade column is now an editable number input
(1-10, `PATCH`es on change), and each row gets a "Remove" action that opens
a confirmation dialog naming the source and its passage count — same
copy/two-step shape as the pre-rewrite page — before calling `DELETE`.
Added a `patch()` helper to `lib/api.ts` alongside the existing get/post/
put/del, since none existed.

### H2 — Uploaded files can never be opened again, by anyone — FIXED

`POST /api/me/files` (`app/main.py:1294-1308`) stores a client's file;
`vault_files.path()` (`app/vault_files.py:35`) can retrieve it by id, but no
route anywhere calls it to serve bytes back. Both
`web/src/routes/(client)/client/files/+page.svelte` and the
practitioner-facing `GET /api/me/clients/{id}/documents`
(`app/main.py:1230`) — and the client-detail document list at
`clients/[id]/+page.svelte:27-34` — only ever show filename/kind, with no
link or action to view content. A patient uploads a lab result and neither
they nor their practitioner can ever read it again, only see that something
with that name exists. Compounding this: `vault.delete_client()`
(`app/vault.py:302-327`) deletes the `uploaded_files` DB rows on erasure but
never deletes the underlying file bytes, so an "erased" client's files stay
on disk indefinitely. [v2/13 M3](../v2/13-known-issues.md#m3) fixed the
*list* of previously-uploaded files; the actual read path was never built,
before or after the rewrite.

**Fixed:** a new `GET /api/me/files/{file_id}` (client-facing) and
`GET /api/me/clients/{client_id}/files` + `.../files/{file_id}`
(practitioner-facing, ownership-checked against the client) serve the
stored bytes with the same inline-pdf/text-else-download + `nosniff`
pattern `/original` already uses. `vault.get_uploaded_file()` looks the row
up by its stored `storage_path` (the on-disk filename actually uses a
*second*, unrelated id generated at upload time — `storage_path` is the
only thing that ever linked the two; worth a closer look separately, not
a functional problem here since the path is stored either way).
`delete_client()` now unlinks each file's `storage_path` before dropping
its row. The client Files page and a new "Files" section on the
practitioner's client-detail page both link to these. Also fixed in the
same pass: the client Files table's columns referenced `f.filename`/
`f.content_type`, fields that don't exist on the real row
(`original_name`/`media_type`) — every file's File/Type cells were
silently blank; and [M8](#m8) (upload errors swallowed to a generic
message) in the same file, while already there.

### H3 — Stripe checkout/portal redirects point at retired pre-rewrite pages — FIXED

`app/billing.py:28-29,72` — `success_url`/`cancel_url`/the billing-portal
`return_url` — all point at `{public_base_url}/static/practitioner/profile.html`.
The live route is `/practitioner/profile`
(`web/src/routes/(practitioner)/practitioner/profile/+page.svelte`).
`billing.py` wasn't updated when the frontend was cut over: a practitioner
finishing checkout or leaving the Stripe billing portal lands on the old,
retired UI instead of the live app.

**Fixed:** all three URLs now point at `/practitioner/profile`.

### H4 — Multi-turn consult history never actually carries forward — FIXED

`streamConsult(clientId, question)` (`consultStream.ts:21-30`) never sends
`session_id`. The backend creates a brand-new session whenever one isn't
given (`app/main.py:992-994`), so `history = vault.session_history(...)`
is always empty from this UI — every "Ask" starts fresh, silently, with no
indication to the practitioner that follow-up context was lost. Related:
the "Continue in Consult" deep link from a client's session list
(`clients/[id]/+page.svelte:21`, `?client=&session=`) is also dropped —
`consult/+page.svelte`'s `$effect` (lines 14-16) only reads the `client`
param, never `session` — so clicking a past consultation lands on a blank
form and, per this same bug, starts yet another disconnected session.

**Fixed:** `streamConsult` now takes an optional `sessionId` and sends it as
`session_id`; the page keeps a `sessionId` state, set from the first
answer's `result.session_id` and reused for every subsequent question, so
follow-ups actually continue the same session. The page now also reads the
`session` query param on load and, when present, fetches
`GET /me/clients/{id}/sessions/{id}` to replay the full prior conversation
(each past turn rendered with the same citations/verdict/librarian view as
a live one — a `turnView` snippet shared between history and the live
result, also folding in [C2](#c2)/[C3](#c3)/[H10](#h10)'s rendering).
Switching clients always starts a fresh session (compared against the
*previous* `clientId`, not an "initialized" flag, so it can't race the
async history fetch above). Answers now render as a running thread of
turns rather than a single replaced block.

### H5 — An unset `VAULT_ENCRYPTION_KEY` silently corrupts stored API keys, then crashes consults with a raw exception — FIXED

`app/main.py:49-50`: an empty `VAULT_ENCRYPTION_KEY` generates a random
Fernet key per-process instead of failing at startup.
`get_config()`'s production fail-closed checks (`app/config.py:100-108`)
cover `session_secret` and `neo4j_password` but not this one. After a
restart, every previously-encrypted `anthropic_api_key_encrypted` becomes
undecryptable; `_decrypt_api_key()` (called at `app/main.py:982`, `1218`)
is never wrapped in try/except, and no global exception handler exists —
so the first consult or session-summary attempt after a restart throws an
unhandled `cryptography.fernet.InvalidToken` instead of a clear "re-enter
your API key" message.

**Fixed:** `get_config()` now fails closed on an unset
`VAULT_ENCRYPTION_KEY` in production, same pattern as `session_secret`/
`neo4j_password`. `_decrypt_api_key()` also now catches `InvalidToken`
(covers the same scenario if it ever recurs, and any other cause of a
mismatched key) and raises a clean 400 telling the practitioner to
re-enter their key, instead of an unhandled 500.

### H6 — "Save session summary" has no UI entry point anywhere — FIXED

The route exists and works
(`POST /api/me/clients/{id}/sessions/{id}/summary`, `app/main.py:1207`,
writing a `session_summary` vault entry) but no file under
`web/src/routes/(practitioner)/**` calls it — not on Consult, not on the
client detail page. README.md's "It remembers" claim has a fully working
backend and zero reachable frontend.

**Fixed:** a "Summarize" button on each session row in the client-detail
page's Sessions list calls the route and shows the saved summary inline.
Also fixed in the same file: each session row linked with `s.question`,
a field that doesn't exist on the real row (`list_sessions()` returns
`title`/`last_question`, never `question`) — every session in the list was
silently showing its raw UUID instead of a readable label.

### H7 — Non-PDF or non-text uploads are silently garbled and ingested as real, graded sources — FIXED

`_extract_pages` (`app/main.py:136-147`) special-cases only `.pdf`;
anything else is `raw.decode("utf-8", errors="replace")`. Uploading a
`.docx`, `.png`, or other binary file doesn't get rejected the way a
scanned (image-only) PDF deliberately is — it produces silently corrupted
text that still gets a full Reader call, a grade, and a place in the
graded library, unlike the deliberate, documented rejection for scanned
PDFs. No file-size or file-type cap exists on any upload path in the app
(admin ingest, public photo signup, or client file upload — grepped, none
found).

**Fixed:** a `.pdf`-named upload must now actually start with the `%PDF`
magic bytes; anything else is decoded as strict UTF-8 (not
`errors="replace"`) and rejected with a clear 400 if that fails — a
`.docx`/`.png`/other binary no longer gets ingested as corrupted "text."
Also added a 20 MB cap on both the admin source-ingest upload and the
client file upload (photo upload was already capped in [C7](#c7)).

### H8 — Reader grading is based on only the first ~20,000 characters of a source, with no warning — FIXED

`llm.read_source()` (`app/llm.py:130-135`) truncates to `text[:20000]`
before the model ever sees it. A long clinical guideline's reliability
grade, summary, and topic tags can all be decided without the model reading
past roughly the first 20k characters, and nothing in the admin UI
indicates a source was truncated for grading purposes.

**Fixed:** `read_source()` now returns whether the input exceeded 20k
characters; `ingest_source()` stores it as `Source.reader_truncated`
(defaulting to `false` via `coalesce` for sources ingested before this
existed), and the admin library shows a "graded from a partial read"
chip on any source where it's true. The truncation limit itself is
unchanged — this makes an existing tradeoff visible, not a bigger-context
change.

### H9 — No password length/strength check at account creation, inconsistent with change-password — FIXED

`change_password` enforces `len(new_password) >= 8` (`app/auth.py:179-182`),
but `practitioner_signup` (`app/main.py:515`), `client_signup`
(`app/main.py:560`), and `superadmin_create_admin` (`app/main.py:606`)
accept any password, including empty or one character. The "At least 8
characters" hint shown on signup/join forms
(`signup/+page.svelte:37`, `join/+page.svelte:57`) is purely cosmetic —
nothing server-side enforces it at registration time.

**Fixed:** a new `auth.check_password_strength()` (same 8-character rule)
is now called from `practitioner_signup`, `client_signup`,
`admin_create_practitioner` (found while fixing this — a fourth,
admin-direct-create path with the identical gap), and
`superadmin_create_admin`. `change_password`'s own existing check is
untouched, left as its own inline check rather than refactored to share
this helper, since it wasn't broken.

### H10 — "How the librarian chose" reasoning is captured by the backend but never shown — FIXED

The Librarian's `reasoning`, `considered`, `opened`, and `truncated` fields
all exist in the real payload (`app/main.py:1098-1099`), but
`consult/+page.svelte` never reads or renders any of them (the frontend
type in `consultStream.ts:15` even expects a top-level `reasoning` field
that doesn't match the real shape). A practitioner has no way to see which
sources were considered versus opened, or why — one of the README's listed
demo capabilities with no working UI.

**Fixed:** in the same change as [C3](#c3), a collapsible "How the
librarian chose" panel now renders `reasoning`, the considered/opened/
truncated counts, and the list of opened sources with their grades.

### H11 — No rate limiting or lockout on login — FIXED

`app/auth.py:127-169` — bcrypt slows brute force somewhat, but there is no
attempt counter, backoff, or lockout of any kind on `/api/auth/login`.

**Fixed:** an in-memory per-email counter (no new dependency, single-process
deployment per specs/v3/11) locks an email out for 15 minutes after 5 failed
attempts within that window, checked before any password verification runs
and cleared on a successful login. Not persisted across a restart — a
restart is itself a rare, high-friction event, and a real deployment
wanting attacker-triggered-restart resistance would need this in a shared
store (Redis or the DB) instead, out of scope for this PoC's scale.

### H12 — A failed consult stream is only reported for one specific exception type — FIXED

`me_consult`'s SSE generator (`app/main.py:1017-1078`) only catches
`anthropic.APIError`. Any other exception — a Neo4j error out of
`knowledge.traverse()` at line 1026, for instance — breaks the generator
with no `error` SSE event emitted at all; the frontend just sees a dropped,
incomplete stream instead of a clear failure message.

**Fixed:** a second `except Exception` catches anything else, logs it
server-side (`logging.exception`, so it's still visible to an operator),
and emits a generic `error` SSE event instead of silently dropping the
stream. The consult page's stuck-"running" UI on error is a separate,
already-tracked gap — [M3](#m3).

---

## Medium

### M1 — Suspended/rejected practitioners' public profile and contact form stay live — PARTLY FIXED

`coach/[id]` is prerendered at build time
(`web/src/routes/(public)/coach/[id]/+page.ts:5`, already flagged generically
in [02](02-open-questions.md)), but `POST /api/practitioners/{id}/contact`
(`app/main.py:545-550`) never checks `status` either — so even after a
practitioner is suspended, their stale static profile page keeps working
and its "Get in touch" form keeps accepting messages to them until the next
rebuild.

**Fixed:** `contact_practitioner` now 404s unless the practitioner is still
`approved` — the stale page can't send anywhere anymore. The page itself
staying visible/browsable until the next rebuild is unchanged — that's the
prerendering tradeoff [02](02-open-questions.md) already tracks, not a
one-route fix.

### M2 — Suspended/rejected practitioners have no way back, in the admin UI — FIXED

`web/src/routes/(admin)/admin/users/+page.svelte:82-88` only renders
Approve/Reject buttons for `status === 'pending'` and Suspend for
`'approved'` — no branch offers re-approval for `'suspended'`/`'rejected'`.
The backend has no such restriction (`admin_approve`,
`app/main.py:710`, applies unconditionally) — this is a pure UI gap, but it
leaves a suspended practitioner permanently stuck from the admin's
perspective.

**Fixed:** an `{:else}` branch (covering both `suspended` and `rejected`)
now shows a "Re-approve" button, reusing the existing `approve()` call.

### M3 — A failed consult leaves the progress UI stuck "running" forever — FIXED

On `{event: 'error'}` (`consult/+page.svelte:44-46`), only a transient
toast fires — nothing marks the in-flight `steps` entries as failed, and
the pulsing `.dot` animation only stops via `class:done`, which never gets
set on error. After the toast disappears, the UI still visually looks like
a request that's in progress, indefinitely.

**Fixed:** a new `failRunningSteps()` marks every still-`running` step
`error` (a red, non-pulsing dot, labelled "failed") whenever an `error` SSE
event arrives or the request throws.

### M4 — No cancellation on a consult stream, and no guard against overlapping requests — FIXED

`streamConsult` (`consultStream.ts:21`) opens a plain `fetch` with no
`AbortController`. Navigating away mid-consult doesn't stop the backend
from finishing (and billing) the Anthropic calls. The Ask button itself is
guarded by `loading`, but the client-switching paths from C8 aren't, so two
overlapping streams writing into the same page-level state remains
possible.

**Fixed:** `streamConsult` now takes an optional `AbortSignal`; the page
creates an `AbortController` per request and aborts it in `onDestroy`
(leaving the page mid-consult). This stops the browser connection and
whatever Anthropic call in the pipeline *hasn't started yet* — the one
already in flight at that moment still finishes server-side, since a
generator can't be interrupted mid-`await`; documented honestly in
`consultStream.ts` rather than claimed as a full stop. The overlap half of
this finding is already closed as a side effect of [C8](#c8)'s fix
(disabling client switching during `asking` also means `clientId`/
`sessionId` can't change mid-request) plus the pre-existing `asking` guard
at the top of `ask()`.

### M5 — Questionnaire editing is backend-only — FIXED

`POST /api/admin/questionnaires/{id}` (`app/main.py:794`) works, but
`web/src/routes/(admin)/admin/questionnaires/+page.svelte` only has a "New
questionnaire" create dialog and a read-only table — no way to edit an
existing questionnaire's questions, toggle `is_active`, or view its full
question list after creation.

**Fixed:** an "Edit" action per row fetches the full questionnaire and
opens the same dialog pre-filled, submitting to the edit route instead of
create. Explicit copy warns that saving creates a new version and makes it
active (matching what `edit_questionnaire`/`_insert_questionnaire` actually
do — every other questionnaire, including the currently active one,
gets deactivated). Scope kept deliberately narrow, matching this page's
existing "one question per line, all plain text" create flow: editing is
lossy for anything beyond a question's prompt text — a real per-question
type/theme/options builder is a bigger, separate piece of work
(`specs/v3/TODO.md` already lists the per-row-control class of UI as
higher-effort and explicitly skipped once before). No `is_active` toggle
either — there's no backend route to flip it independent of creating a new
version.

### M6 — Wearable connections have no disconnect — FIXED

`web/src/routes/(client)/client/wearables/+page.svelte:32-33` shows a
static "Connected" chip once true, with no disconnect action, and
`app/wearables.py` registers `connect`/list/`callback` routes but no
`disconnect`/revoke route anywhere. A client who connects the wrong
provider account has no way to undo it.

**Fixed:** a new `DELETE /api/me/wearables/{provider}` (backed by
`vault.delete_wearable_connection()`, which also drops that provider's
fixture data points, not just the connection row) plus a "Disconnect"
button next to the Connected chip.

### M7 — Directory search inflates a practitioner's profile-view count on every listing, not just opens — NOT A BUG, RETRACTED

`list_practitioners_public` (`app/main.py:479-490`) calls
`core_store.log_profile_view(p["id"])` for every card in a filtered result
list — every visit to the public directory search inflates every matching
practitioner's view count, not just genuine profile opens.

**Retracted on closer check:** [specs/v2/03-website.md §Analytics](../v2/03-website.md#analytics)
explicitly specs this: *"Every directory listing render and every
coach-detail-page render logs a `profile_view_events` row."* This is
impression tracking working as designed, not a bug — flagged here rather
than silently dropped so the original (mistaken) finding is on record, per
this document's own standard of recording what was checked.

### M8 — Client file-upload errors are swallowed to a generic message — FIXED

`web/src/routes/(client)/client/files/+page.svelte:19-22` throws a
hardcoded `'Upload failed.'` on any non-OK response instead of reading the
real `detail` from the response body — unlike the admin ingest form, which
does surface the backend's actual error. A client hitting a real
validation failure (bad file type, size limit) gets no useful reason why.

**Fixed:** in the same [H2](#h2) pass, since it's the same file — now reads
`res.json()`'s `detail`/`detail.message` before falling back to the generic
string.

### M9 — `GET /api/sources` has no upper bound on `per_page`

`list_sources` (called from `app/main.py:256-265`) clamps `page = max(1,
page)` but never clamps `per_page` — a caller can request an arbitrarily
large page in one query.

### M10 — Unhandled type-conversion crash updating a practitioner's profile numbers

`app/main.py:827-828`: `int(value)` on `years_experience`/
`consultation_price_cents` from a multipart form has no try/except — a
non-numeric value throws an unhandled exception (raw 500) instead of a
clean 400.

### M11 — `_json_call` throws an unhandled `StopIteration` if a model response has no text block

`app/llm.py:44`: `next(b.text for b in response.content if b.type ==
"text")` has no default/guard for the case where the response has none.

### M12 — Blank consult questions still run (and bill) the full pipeline

`MeConsult.question: str` (`app/main.py:961`) has no `min_length` or
`.strip()` check — an empty submission still runs the full, billed
Librarian → Specialist → Checker sequence.

### M13 — Client dashboard tiles use emoji icons — the same problem already fixed once

`web/src/routes/(client)/client/dashboard/+page.svelte:11-13` uses raw
emoji (📋📁⌚). Commit `5e0c14f` explicitly replaced the practitioner
sidebar's mixed emoji/unicode icons with the stroke-based `Icon` component
for exactly this reason ("not 'professional single-color'") — that fix was
never applied to the client dashboard.

### M14 — Client dashboard tiles show static copy, not real status

Same file: "Fill in" / "Upload" / "Connect" never change even though
`data.response`, `data.files`, `data.connections` are all available
elsewhere in the same portal — a client who already submitted the
questionnaire or connected a wearable sees the identical call-to-action as
one who hasn't.

### M15 — Pro-gated practitioner nav items aren't marked as gated

`web/src/routes/(practitioner)/practitioner/+layout.svelte:6-14` shows
Consult/Clients/Knowledge identically for Basic and Pro plans (the layout
guard at `+layout.ts:16` checks only role, not plan). A Basic practitioner
only discovers the paywall after clicking in and getting a 403 toast,
rather than seeing a lock or "Pro" badge up front.

### M16 — Self-flagged: an active library filter can silently hide a source right after ingesting it

In this review's own `web/src/routes/(admin)/admin/+page.svelte`,
`ingest()` calls `invalidateAll()` to refresh `data.sources`, but the
`q`/`activeTopic`/`activeKind` filter state isn't reset. If a category
filter is active and the newly ingested source is tagged with a different
topic, it won't appear in the filtered list — the toast just says "Source
ingested," with nothing indicating the new source is filtered out of view.

### M17 — Stale, transient flash of logged-out nav state on every load

`PublicNav.svelte:18` fetches session state in `onMount`, so on every page
load `session` starts `null` and the nav renders "Log in / Get started"
first, then flips to "Dashboard" a round trip later. The recent fix
(referenced in `PublicNav.svelte:13-16`) addressed the *permanent*
wrong-state bug but not this transient one — an already-logged-in visitor
still sees, and could click, the logged-out CTA for one round trip on
every navigation.

### M18 — Superadmin/admin-role staleness has one more instance than C9 — RESOLVED (via C9)

Noted separately from C9 because it's a narrower version of the same root
cause: `require_admin` does re-fetch `is_active` live, and
`require_pro_practitioner` does re-fetch plan/status live — both correct.
Only the `admin_role` claim on the session cookie (superadmin vs. plain
admin, C9) was never given the same live-recheck treatment. Recorded here
as confirmation that the fix pattern needed is narrow and already
established elsewhere in the same file, not a new mechanism.

C9's fix is exactly that pattern applied to the one missing spot — no
separate change needed.

---

## Low

### L1 — Inconsistent post-login redirect fallback

`login/+page.svelte:20` falls back to `/admin` when a role isn't in the
`LANDING` map; `PublicNav.svelte:35` falls back to `/account` for the
identical lookup. Currently dead code (the backend only ever returns
`admin`/`practitioner`/`client`, all present in `LANDING`), but the two
fallbacks disagree, and one of them routes an unrecognized role to an
admin-only page.

### L2 — No email-format validation, client or server side

`email: str` fields on signup/login accept any string;
`type="email"` on the shared `TextField` gives only HTML5's easily-bypassed
built-in check, and nothing server-side re-validates format before
persisting it as the account's login identifier.

### L3 — Inconsistent confirmation pattern on destructive admin actions

`web/src/routes/(admin)/admin/users/+page.svelte:31` uses a native
`confirm()` for Suspend — the app's own `Dialog` component is used
everywhere else — while Reject (lines 26-29), similarly consequential, has
no confirmation at all.

### L4 — Dead `type="submit"` on two dialog footer buttons

In both `users/+page.svelte:115` and `questionnaires/+page.svelte:65`, the
"Create" button sits in the `Dialog`'s `footer` snippet, which renders as a
sibling of the `<form>`, not inside it (`Dialog.svelte:29-30`) — so
`type="submit"` does nothing there; only the explicit `onclick` handler
actually submits. Harmless today, misleading markup, repeated twice.

### L5 — Questionnaire submission doesn't refresh persisted state

`client/questionnaire/+page.svelte:26-32` shows a success toast on submit
but never re-fetches `data.response` — revisiting the page later without a
full reload won't show the "already submitted" state.

---

## What was checked and found correct

Worth recording so a future pass doesn't re-litigate these: `svelte-check`
across the whole SvelteKit app runs clean (0 errors) as of this review.
`require_pro_practitioner` (unlike the `admin_role`/C9 gap) correctly
re-fetches live plan/status on every request, not from the session cookie.
The practitioner `upgrade` page's flow is straightforward and correct.
Practitioner `contacts`/`profile` form validation was skimmed with nothing
anomalous found (not exhaustively verified — see the methodology note at
the top of this document).
