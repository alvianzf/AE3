# 08 · HTTP API

JSON over HTTP, FastAPI, same conventions as v1/v2
([v2/08-api.md](../v2/08-api.md)). Three changes this version: the consult
route's response shape (bounded retry, [07](07-ai-team.md)), one new route
(session summary), and an experimental use of the HTTP `QUERY` method on
read endpoints that take a body. Everything not called out below is
unchanged — this doc still lists every route so it stays a complete
snapshot, per the versioning convention.

## Page routes vs. API routes

Unchanged from v2 — see [v2/08-api.md](../v2/08-api.md#page-routes-vs-api-routes).

## Public (no auth)

Unchanged from v2 — `GET/POST /api/practitioners*`, `POST
/api/practitioners/{id}/contact`, `POST /api/clients`, `POST
/api/auth/login`, `POST /api/auth/logout`, `POST /api/stripe/webhook`, `GET
/api/me/wearables/{provider}/callback`, `GET /api/health`.

## Any authenticated role

Unchanged from v2 — `GET /api/auth/me`, `POST /api/auth/change-password`.

## Practitioner (Basic or Pro, own resources only)

Unchanged from v2 — profile, contacts, upgrade, billing portal.

## Practitioner (Pro only)

All routes unchanged from v2 except:

| Route | Purpose |
|---|---|
| `POST /api/me/consult` | Ask a question about a client — Librarian → Specialist → Checker with their key, now with one bounded retry when the first verdict is `weak` ([07](07-ai-team.md)). Response gains `revised: bool`. Now streamed ([below](#live-progress-stream)) rather than a single JSON body. 400 if no key is on file yet. |
| `POST /api/me/clients/{id}/sessions/{session_id}/summary` | **New.** Runs the Summariser against that session's turns, saves the result as a `session_summary` vault entry, returns the summary text. Pro only, own client only — 404 across tenants, same rule as every other client-scoped route. |

`GET /api/me/clients/{id}/sessions`, `GET
/api/me/clients/{id}/sessions/{session_id}`, and the rest of the Pro
practitioner surface (documents, intake, knowledge weights, notifications)
are unchanged from v2 — see [v2/08-api.md](../v2/08-api.md#practitioner-pro-only)
for the full table.

## Client / Admin / Superadmin

Unchanged from v2 — see [v2/08-api.md](../v2/08-api.md) for the full tables.

**Not built**: a route to delete a practitioner outright, and a route
exposing a Pro practitioner's own vault audit trail — both carried forward
as known gaps ([10](10-security.md)).

## HTTP `QUERY` method — experimental, read endpoints with a filter body

Several read endpoints (the practitioner directory filter, the admin
practitioner roster, the shared library's source search) take filter
parameters that don't fit cleanly in a query string (multi-value specialty
lists, grade-threshold ranges) and today are either forced into repeated
query params or, where that got unwieldy, into a `POST` — which is
technically wrong for a read and makes the response uncacheable.

v3 adds the `QUERY` method ([IETF draft-ietf-httpbis-safe-method-w-body](https://www.ietf.org/archive/id/draft-ietf-httpbis-safe-method-w-body-04.html))
as the **preferred** way to call these specific endpoints, with `POST` kept
as a fallback — this is a still-draft HTTP method, not yet uniformly
supported by proxies, CDNs, or older HTTP clients, so it cannot be the only
way in.

- **Where it applies**: `GET /api/practitioners` (directory filter), `GET
  /api/admin/practitioners` (roster filter), and the library's source search
  — each gains a `QUERY` variant at the same path, body-shaped like the
  existing query-string filters, same handler, same auth, same response.
  Every other route is untouched; `QUERY` is not adopted for anything that
  writes or that doesn't already exist as a `GET`.
- **Server side**: FastAPI/Starlette dispatch on the method string, so
  `@app.api_route(path, methods=["GET", "QUERY"])` on the same handler is
  enough — no new framework. The deployment's reverse proxy
  (Cloudflare, [11](11-operations.md)) needs to be confirmed to pass the
  `QUERY` method through unmodified before this is relied on in production;
  until that's verified, treat `POST` as the real path and `QUERY` as
  best-effort.
- **Client side**: `fetch(url, {method: "QUERY", body: ...})` works in
  current evergreen browsers that implement the draft; `shared.js` gets a
  small helper that tries `QUERY` and falls back to the existing `POST` path
  on a network-level failure (not a 4xx/5xx — that's a real error, not a
  missing-method signal), so a browser or intermediary without `QUERY`
  support degrades silently rather than breaking the page.
- **Not adopted for `/api/me/consult`**: despite taking a body and being
  read-shaped in one sense (it doesn't mutate the client record), a
  consultation writes a vault turn as a side effect and is not safe/
  idempotent/cacheable — it stays `POST`.

## Live progress stream on `POST /api/me/consult` {#live-progress-stream}

New this version, prompted by a direct ask: the practitioner should see
*which* of the seven AI-team roles is running and *how many tokens* it's
using, live, not just a spinner for the ~40-70s the request takes.

`POST /api/me/consult` changes response type from a single JSON body to
`text/event-stream` (FastAPI `StreamingResponse`) — this is a breaking
change to the route's contract, noted here rather than added as a silent
side channel, since anything calling this route as plain JSON needs to
change. Events, one per line as `data: {...}\n\n`:

```
data: {"event": "agent_start", "agent": "librarian"}
data: {"event": "agent_done", "agent": "librarian", "input_tokens": 1840, "output_tokens": 96}
data: {"event": "agent_start", "agent": "specialist"}
data: {"event": "agent_done", "agent": "specialist", "input_tokens": 3210, "output_tokens": 412}
data: {"event": "agent_start", "agent": "checker"}
data: {"event": "agent_done", "agent": "checker", "input_tokens": 2980, "output_tokens": 58}
data: {"event": "result", "answer": "...", "verdict": "pass", "revised": false, "sources": [...], "reasoning": "...", "total_input_tokens": 8030, "total_output_tokens": 566}
```

- **Granularity is per-agent-call, not per-token.** Each of the seven roles
  is one non-streaming Anthropic API call ([07](07-ai-team.md)) — true
  token-by-token streaming would mean switching every role to streaming
  completions, a materially bigger change to `app/llm.py` than this ask
  needs. "Real-time" here means the practitioner sees each step the moment
  it starts and the moment it finishes with that call's actual usage
  numbers (from the Anthropic response's `usage` field, not an estimate) —
  live relative to the ~40-70s request, not live relative to generation.
  If a future version wants token-by-token, that's a `07-ai-team.md` change
  (streaming completions), not a toast/UI change.
- **On the bounded retry** ([07](07-ai-team.md)): a `weak` verdict emits
  `agent_start`/`agent_done` for `specialist` and `checker` a second time
  before the final `result` event, so the retry is visible as itself, not
  hidden inside a longer wait.
- **Errors**: an `{"event": "error", "message": "..."}` event in place of
  `result`, matching the 502 case in [Failure modes](#failure-modes) below
  — the stream ends either way, never left open.
- **Client side**: `fetch()` with a `ReadableStream` reader, not
  `EventSource` (which cannot send the `POST` body a consult request
  needs). `shared.js` gets one small SSE line-parser used by `consult.html`
  to feed [15 · Design system](15-design-system.md#live-agent-toast)'s
  toast.

## Failure modes

Unchanged from v2, plus: `POST /api/me/consult` now catches an Anthropic API
failure at any step (Librarian, Specialist, Checker, or the retry) and
returns a structured 502 with a "the AI service is temporarily unavailable,
try again" message instead of an unhandled exception — closing a gap the v3
review found (no error handling existed on this path; only ingest-time calls
had a non-fatal degrade).
