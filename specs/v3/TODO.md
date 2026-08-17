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
- [ ] `consult.html`: wire the parser to an `md-snackbar` — role label in
      plain language, running token total, retry-aware copy, collapses to
      the verdict badge on `result`.

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
      a Node toolchain there.
- [ ] Migrate pages one at a time (see order below), verifying each against
      its existing spec section (03/04/05/06 — unchanged this version) before
      moving to the next:
  1. `login.html` — **done**, `npm run build` verified clean; **not yet
     checked in an actual browser** (no display in the sandbox this was
     built in). Both signup flows still pending.
  2. `account.html` — text fields + the password-visibility toggle, replaced
     by `md-outlined-text-field`'s built-in trailing icon.
  3. Shared shell (sidebar, breadcrumbs, topbar user menu) — stays hand-built
     CSS per [15](15-design-system.md), but re-themed with MD3 tokens so it
     matches the components migrated around it.
  4. Practitioner portal (5 pages).
  5. Admin portal.
  6. Client portal.
  7. Public site (about, directory, coach detail).
- [ ] Remove `wirePasswordToggles()` from `shared.js` once every password
      field has migrated to `md-outlined-text-field`.

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
