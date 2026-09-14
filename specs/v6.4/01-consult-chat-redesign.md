# Consult page rebuilt as a chat interface

The consult page (`web/src/routes/(practitioner)/practitioner/consult/
+page.svelte`) was a top-form-plus-list layout: an "Ask" form above a
flat list of past turns, no persistent history, plain-text answers. It
was requested to become a real chat interface, "copy what GPT and
Claude do" — built across several same-day iterations.

## Layout

- **Sidebar** (fixed `18rem` column): a searchable client list (capped
  at ~5 visible rows via `max-height`, the rest scroll), a per-client
  conversation history list, and a patient info widget (name, email,
  DOB, country — the client fields `GET /me/clients` already returns,
  no new endpoint needed).
- **Chat column**: the message thread scrolls independently
  (`overflow-y: auto`), the composer (mode toggle + textarea + send
  button) stays pinned to the bottom via flex layout, not `position:
  sticky` — `.chat-main` is `display: flex; flex-direction: column`
  with the thread as the only `flex: 1 1 auto` child.

History was already server-side (`GET /me/clients/{id}/sessions`,
existing endpoint, used elsewhere on the client detail page) — this
just surfaces it in the consult page itself and makes clicking a past
session load its full transcript and continue it (same session_id, so
the next "Ask" appends to it rather than starting fresh).

**Session history and context stay strictly per-session.** Confirmed,
not just assumed: `vault.session_history()` filters by `WHERE
session_id = %s` inside a per-practitioner Postgres schema
(`vault_connection(practitioner_id)`), and `/api/me/consult` validates
a passed `session_id` belongs to the requesting practitioner and the
given client before using it. A session's prior turns are fed to the
Reasoner as context (`app/main.py`'s `history_block`, last 6 turns) —
there is no path for one session's turns to leak into another's
context, or across clients/practitioners.

## Visual details, each from a specific request

- **Calendar-style date badge** on each history row: a rounded square,
  a big bold day number, a 3-letter month underneath — styled after
  the iOS Calendar app icon, not a plain date string.
- **Mode toggle** (deep research vs. general lookup) as a segmented
  pill control instead of a `<select>` dropdown.
- **Markdown rendering** (`$lib/markdown.ts`, `marked` + `DOMPurify`)
  instead of plain text, with `[K1]`/`[S1]` citation markers turned
  into clickable buttons *after* sanitizing (so DOMPurify never needs
  to allow `button`/`data-*` for arbitrary LLM output).
- **Sources as a closed-by-default accordion** — a native `<details>`
  with the native marker suppressed in favor of a rotating chevron
  icon, so a long source list isn't always taking up vertical space.
- **A spinner, not just a pulsing dot**, on the currently-running
  pipeline step, plus a temporary "assistant" bubble under the user's
  question showing live step progress while a turn streams.
- **Mode label** on both the question and answer bubble of each turn
  (`retrieval_mode`, already present in the stored turn payload —
  no backend change needed for this one).
- **Proper line icons** (`$lib/components/Icon.svelte`, extended with
  `chevron`/`search`/`new-chat`/`calendar`/`globe`/`send`/`bolt`/
  `user-card`) replacing plain text labels and an icon-only circular
  button, matching the existing icon system already used by
  `AppRail`.

## Two live bugs found and fixed

**Sidebar/composer overlap.** Screenshot from production: the composer
rendered overlapping the sidebar's history list. Cause: CSS grid and
flex items default to `min-width: auto`, which lets an item's
intrinsic content width (a long unbroken title or date string) force
it wider than its track/flex-basis instead of respecting it — a
classic, easy-to-miss overflow gotcha. Fixed by adding `min-width: 0`
down the affected chain: `.chat-shell`'s sidebar column track,
`.sidebar`, `.sidebar-block`, `.chat-main`, and the history row
button.

**0-turn "ghost" sessions.** `vault.create_session()` runs as soon as a
question is sent, but a turn is only written once the stream finishes
— an aborted request or a mid-stream crash leaves a session row with
no turns behind. Several of these, with duplicate titles, were
cluttering the history list. Filtered out client-side (`sessions.
filter(s => s.turns > 0)`) rather than shown, since a 0-turn session
has nothing to resume anyway.
