# v3 implementation TODO

Ordered so each stage leaves a working, deployable app — no stage depends on
a later one. Tests are explicitly out of scope for this pass.

## 1. Security fixes (small, independent, do first)

- [ ] `app/config.py`: remove hardcoded fallback values for `session_secret`
      and `neo4j_password`; raise at startup if unset and `ENV=production`.
- [ ] `app/main.py` / `.env.example`: document both as required-in-production
      alongside `VAULT_ENCRYPTION_KEY`.

## 2. AI-team changes ([07](07-ai-team.md), [08](08-api.md))

- [ ] `app/main.py` (`me_consult` handler): wrap the Librarian → Specialist →
      Checker call sequence in error handling; return structured 502 on any
      Anthropic API failure instead of an unhandled exception.
- [ ] Same handler: on `verdict == "weak"`, call `answer()` again with the
      `unsupported` claims list appended to context, then `check()` once
      more; pick the better-verdict answer; add `revised: bool` to the
      response payload. Hard-cap at one retry in code.
- [ ] `static/practitioner/consult.html` / `app.js`: render the `revised`
      flag ("first draft was revised after an internal check") when true.
- [ ] New route `POST /api/me/clients/{id}/sessions/{session_id}/summary`:
      load the session's turns, call `summarize_session()`, save as a
      `session_summary` vault entry via the existing (already-implemented,
      currently unused) `vault.py` entry kind, return the summary text.
- [ ] Add a "Summarize this consultation" action somewhere reachable in the
      practitioner UI (client detail page's session view is the natural
      spot) — currently the only gap is that no UI calls the new route
      either.

## 3. Live progress stream ([08](08-api.md#live-progress-stream))

- [ ] `app/main.py` (`me_consult`): convert to `StreamingResponse`
      (`text/event-stream`); emit `agent_start`/`agent_done` (with
      `input_tokens`/`output_tokens` from each Anthropic response's `usage`
      field) around each of the Librarian/Specialist/Checker calls and the
      retry pair; emit a final `result` event with the existing payload plus
      `total_input_tokens`/`total_output_tokens`; emit `error` in place of
      `result` on failure.
- [ ] `app/llm.py`: confirm `.usage` is actually present on the response
      object for the pinned Anthropic SDK version — checked the three call
      sites (lines 27, 450, 523) and none currently reads it, so this is
      unverified, not assumed. If present, thread it back to the caller. If
      not (SDK too old, field renamed), the token-count half of the toast is
      dropped, not faked with an estimate — the role/status line ships
      either way.
- [ ] `shared.js`: small SSE line-parser (`fetch` + `ReadableStream`, not
      `EventSource`, since the request needs a POST body).
- [x] `app/main.py` / `shared.js` / `consult.html`: SSE stream, `postSSE()`
      parser, and a live toast wired up — **shipped as a stopgap element**
      (`agentToast()` in `shared.js`), not an `md-snackbar`, since this
      landed before the MD3 build pipeline existed. Swapping it to
      `md-snackbar` is now unblocked but not yet done — folded into the
      MD3 pass below rather than tracked separately.

## 4. Material Design 3 / build step ([11](11-operations.md), [15](15-design-system.md))

- [x] Add `package.json`, `package-lock.json`, `vite.config.js`.
- [x] Add `@material/web` dependency.
- [x] Generate MD3 `theme.css` from the current brand seed color
      (`scripts/gen-theme.mjs`, seed `#9c3f5a`).
- [x] Set up `static/dist/` as Vite's build output; added to `.gitignore`;
      confirmed the existing FastAPI `/static` mount serves it unchanged
      (no new route needed).
- [x] Add `.nvmrc`, pin Node version (22).
- [ ] Update deploy pipeline: `npm ci && npm run build` before app start —
      not yet done on the live host; the current deploy still ships without
      a Node toolchain there. **Not yet deployed to production at all** —
      everything in this section is committed to `main` only.
- [ ] **No page has been checked in an actual browser** — every migration
      below is verified only by `npm run build` succeeding and a Node
      syntax check (`node --check`) on the built JS and each page's inline
      script. That catches syntax errors, not rendering/layout/behavior
      bugs. Treat every "done" below as "builds clean, unseen."
- Migrated (forms/buttons only — see per-page notes for what was
  deliberately left native):
  - [x] `login.html`
  - [x] `practitioner-signup.html`, `client-signup.html`
  - [x] `account.html`
  - [x] Shared shell tokens (`static/style.css`'s `--accent`/`-ink`/`-soft`
        now read `var(--md-sys-color-*, <original hardcoded value>)`) — the
        shell markup itself (sidebar, breadcrumbs, topbar) stays hand-built
        CSS, not migrated to components; only its color tokens harmonize
        with MD3 pages now. No dark-mode reconciliation (site has none).
  - [x] Practitioner portal: `clients.html` (add-client form),
        `consult.html` (Ask button only — question `<textarea>` and the
        agent-progress toast left native, see above), `profile.html`
        (API key field, profile edit form), `upgrade.html`,
        `contacts.html` (status filter → `md-outlined-select`)
  - [x] Admin portal: `users.html` (status filter, both create forms),
        `questionnaires.html` (title field, the three builder-level
        actions — not the per-question builder)
  - [x] Client portal: `files.html` (Upload button)
  - [x] Public site: `coach.html` (contact form)
  - [ ] `dashboard.html` (all three portals) — no form controls to migrate,
        left entirely untouched (no theme.css link either — no MD3
        components on the page, linking the theme would just tint hand-
        built elements slightly differently than their hardcoded values
        for no benefit)
- **Explicitly left native, each for a specific, checked reason** (not
  just general caution):
  - [ ] `directory.html`'s specialty/language filters — confirmed the page's
        own JS reads `.options.length` (`static/public/directory.html:134`),
        a native-`<select>`-only property `md-outlined-select` doesn't have.
        Migrating would silently break that check, not just look different.
  - [ ] `client/questionnaire.html` — entire form is built per-question from
        a runtime type switch (text/number/date/select/textarea) including
        a dynamically populated `<select>`. Highest-risk dynamic-form page
        on the site; skipped rather than guessed blind.
  - [ ] Dynamically `.map()`-templated per-row controls: `knowledge.html`'s
        per-source weight input/save button, `client-detail.html`'s tab/
        save-note/save-doc/toggle-status buttons, `contacts.html`'s
        per-row mark-contacted/closed buttons, `users.html`'s per-row
        approve/reject/suspend/plan/role buttons, `wearables.html`'s
        per-provider connect buttons. MD3 buttons are also likely
        oversized for this density — not just a migration-risk question.
  - [ ] `practitioner-signup.html`'s photo file input, `profile.html`'s
        photo file input — `@material/web` has no file-picker component.
  - [ ] `client-signup.html`'s practitioner `<select>` — dynamically
        populated (same class of risk as the directory filters, not yet
        confirmed to break anything specific the way `.options.length`
        does, but not checked either).
- [ ] Remove `wirePasswordToggles()` from `shared.js` — **not done, and
      can't be yet**: `account.html`'s own DOMContentLoaded-time call to it
      was never removed, and several unmigrated pages (v2.14's site-wide
      toggle) still depend on it for their plain `<input type=password>`
      fields. Only safe to remove once every password field on the site has
      migrated — currently true for login/both-signups/account/np-password/
      na-password/ak-key, not yet true site-wide.

## 5. HTTP QUERY method ([08](08-api.md))

- [ ] Confirm with the hosting/proxy setup whether Cloudflare passes an
      unrecognized `QUERY` method through unmodified (test against a
      throwaway route before wiring real endpoints).
- [ ] Add `QUERY` to `methods=[...]` alongside `GET` on: `/api/practitioners`,
      `/api/admin/practitioners`, source search.
- [ ] `shared.js`: helper that attempts `QUERY`, falls back to `POST` on a
      network-level failure (not a 4xx/5xx).
- [ ] Skip `/api/me/consult` — explicitly not a QUERY candidate, stays POST.

## Explicitly deferred (not in this TODO)

- Librarian empty-result fallback UX (grade-threshold broadening, admin
  "add a source" nudge) — real finding, deferred to keep this version to a
  reviewable size; not blocked by anything above.
- Reader/Indexer shared-context pass (reduce topic/concept vocabulary drift)
  — same reasoning.
- Everything already deferred in v2 (backups, encryption at rest, GDPR
  apparatus, practitioner hard-deletion, rate limiting).
