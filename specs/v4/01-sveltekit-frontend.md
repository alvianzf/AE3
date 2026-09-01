# 01 · Frontend rewrite: SvelteKit

Requested directly: "as a really world level UI UX designer, tear down the
app, build a new FE that is better, more user friendly, less cramped, and
much better while keeping the gradient color since user love it... write it
in Sveltekit." **Spec only** right now — no code, nothing touches
production until this is reviewed.

**Deployment target: the static adapter, with per-route prerendering for
the public portal — not adapter-node.** This document originally specced
adapter-node (real SSR, a new Node server process in production), confirmed
in an earlier round. Revisited once the memory math below was on the
table: **"reactive" and "SSR" are two different things that got
conflated.** Svelte's reactivity — components updating live, forms, the SSE
consult stream — is a client-side/hydration concern, identical whether a
page arrives as a server-rendered response or a static shell. SSR's actual
payoff is faster first paint and SEO, and three of this app's four portals
(client/practitioner/admin) sit behind login — a search engine never sees
them, and first-paint speed on an authenticated dashboard isn't a
conversion-critical moment the way it is on a public marketing page. Only
the public portal (directory, coach profiles, about) plausibly benefits
from SSR/SEO, and SvelteKit's per-route `export const prerender = true`
gets that exact benefit at *build* time, with no server needed per request.
Net effect: **zero new Node process in production** — FastAPI keeps serving
the build output from `/opt/clinic/static` exactly like it serves
`static/dist/` today, and the entire memory-risk section this document
used to carry is eliminated, not mitigated. See
[§Deployment](#deployment-static-adapter-fastapi-keeps-serving-it) for the
concrete version of this.

**This reverses a standing decision, not just a big addition** —
[v3/01-overview.md decision 5](../v3/01-overview.md#decisions): *"v2 keeps
v1's stack: FastAPI · Neo4j · SQLite · Anthropic · vanilla JS. No new
framework introduced for the public website or the additional portals."*
That held through v3's own Material Web adoption
([v3/15](../v3/15-design-system.md), which explicitly chose *"hand-writing
MD3's tokens as vanilla CSS, keeping the buildless approach"* as the
rejected alternative — i.e., v3 already stretched the no-framework rule as
far as it would go without breaking it). SvelteKit breaks it. Per
[specs/README.md](../README.md)'s own versioning rule — *"a new version is
cut when there's a change worth auditing: new scope, a reversed
decision"* — that's exactly what this is, so it's `v4/`, not another
numbered doc bolted onto `v3/`.

**Status: spec only, not approved, not implemented.** No `.svelte` file
exists, no `npm create svelte` has been run, no deploy config changed.
Formally cutting `v4/` the way `specs/README.md` describes (copy forward
every unchanged doc from `v3/`, freeze `v3/` as superseded) is a mechanical
step for whoever approves this direction — doing it speculatively, before
the direction itself is approved, would mean maintaining two copies of 15+
documents that may never diverge. This single doc is the actual proposal;
[02](02-open-questions.md) is the honest risk/tradeoff ledger a decision-maker
needs before greenlighting it.

---

## What doesn't change

Everything this rewrite is presentation-layer only, same framing
[v3/15](../v3/15-design-system.md) used for Material Web:

- **Product scope, IA, the four-portal structure** — [v3/01](../v3/01-overview.md)
  through [06](../v3/06-client-portal.md), [09](../v3/09-payments.md).
  Golden paths 1 and 2 from [v3/17](../v3/17-full-app-redesign.md#redesign-direction)
  are the paths this rewrite has to preserve, not redesign.
- **Backend, data model, auth model** — `app/main.py`'s route surface
  ([v3/08](../v3/08-api.md)), `app/auth.py`'s cookie-session mechanism,
  Neo4j/SQLite/vault architecture ([v3/02](../v3/02-data-model.md)). FastAPI
  stays the only thing that talks to Neo4j, SQLite, and Anthropic.
- **The visual identity.** Explicitly kept per the request: the floating
  red gradient sidebar (`.sidebar`, lighter top `rgba(203,44,68,.88)` to
  darker bottom `rgba(64,6,16,.94)`, [v3/15 §Glass finish](../v3/15-design-system.md#glass-finish)),
  the unfilled floating topbar, frosted-glass `.card-panel`s over the
  botanical backdrop (`--glass`/`--blur` tokens, the drifting radial-gradient
  wash, the leaf-pattern SVG), `.ph.botanic`'s red header bands, the `.step`
  numbered markers, `.vine`/`.leaf` dividers, the `.leafmark` watermark, the
  full motion layer (`liftIn`/`slideL`/`popIn`/`sway`/`breathe`, all
  `prefers-reduced-motion`-gated). These are re-implemented as Svelte
  components/CSS custom properties, not redesigned — see
  [§Visual system](#visual-system-keeping-the-identity-fixing-the-density) for exactly what's kept
  literally vs. what's restructured to fix "cramped."

## What does change

- **Every page becomes a Svelte component**, file-based routing instead of
  24 hand-written HTML files each with their own inline `<script>`.
- **`@material/web` is dropped.** See [§Component strategy](#component-strategy-drop-material-web-not-svelte-native)
  for why — this is the single biggest architectural fork in this document
  and it's argued, not asserted.
- **A real component library** replaces every hand-rolled pattern currently
  duplicated per-page: the datatable (`static/style.css`'s `.data-table`,
  currently copy-pasted markup+JS across `admin/users.html`,
  `admin/dashboard.html`, `admin/questionnaires.html`,
  `practitioner/clients.html`), the dialog pattern (`admin/users.html`'s
  `#np-dialog`/`#na-dialog`, `practitioner/clients.html`'s `#cl-dialog`),
  the tab pattern (three different implementations today —
  [v3/17 X2](../v3/17-full-app-redesign.md#x2--medium-three-tab-idioms-one-md3-component-that-should-replace-all-of-them)),
  the sidebar/topbar shell (currently pasted byte-for-byte into all ~24
  pages), the checklist, chips, buttons, toasts.
- **Density**, restructured properly instead of patched. The MD3
  field-density bug ([v3/15 §Field density](../v3/15-design-system.md#field-density)
  — 16px default padding/content-size overriding this app's 15px body text,
  plus `md-outlined-select`'s hardcoded 210px `min-width` literally
  overlapping two dropdowns on `admin/users.html` until it was patched with
  a CSS override) is the concrete symptom of "cramped": a component
  library's own opinions fighting the app's density at the token level.
  Dropping MD3 removes the fight entirely — see [§Visual system](#visual-system-keeping-the-identity-fixing-the-density).

---

## Visual system: keeping the identity, fixing the density

### Token strategy: CSS custom properties, carried forward almost unchanged

`static/style.css`'s `:root` tokens (`--glass`, `--blur`, `--accent`,
`--r`/`--r-lg`, `--shadow`/`--shadow-lg`, `--ease`) are not a
Material-Web-generated theme (`theme.css`) — they're hand-written, framework-
agnostic CSS custom properties that already work exactly the way a Svelte
app wants tokens to work: set once, consumed everywhere via `var()`, no
build-time generation step to reproduce. **These move into SvelteKit's
global stylesheet (`src/app.css` or a `<style>` block in the root layout)
close to verbatim.** The only tokens that get dropped are the MD3
interop shims `style.css` currently carries for pages that haven't migrated
yet:

```css
/* static/style.css today — MD3 fallback interop, dropped in v4 */
--accent: var(--md-sys-color-primary, #9c3f5a);
--accent-ink: var(--md-sys-color-on-primary-container, #7d2f47);
--accent-soft: var(--md-sys-color-primary-container, #f7eaee);
```

becomes a plain, single-source token with no `var(--md-sys-*, fallback)`
indirection:

```css
--accent: #9c3f5a;
--accent-ink: #7d2f47;
--accent-soft: #f7eaee;
```

The gradient sidebar, the botanical backdrop (`body::before`/`body::after`
in `style.css`, the radial-gradient drift + the inline-SVG leaf field), the
`.leafmark` watermark, `.step`, `.vine`/`.leaf`, and the full motion
`@keyframes` set (`liftIn`, `slideL`, `popIn`, `sway`, `breathe`, the
`prefers-reduced-motion` override) all move over as literal CSS, because
none of it was ever MD3-dependent — it's the app's own hand-built layer
that MD3 sat inside of, per [v3/15](../v3/15-design-system.md)'s own
framing ("the hand-built shell... stays visually consistent with the MD3
components sitting inside it"). Dropping MD3 doesn't touch any of it.

### Spacing/type scale: made explicit instead of ad hoc

Today's density problems aren't really about MD3 — they're that
`static/style.css` never had an explicit scale to begin with. Padding
values are handwritten per-component (`.btn` is `.55rem .9rem`, `.pb` is
`1rem`, `.pb.tight` is `.6rem`, `.data-table td` is `.55rem .6rem`, dialog
content is whatever inline `style="display:grid;gap:.4rem"` a given page
happened to use) — consistent by convention and careful copy-pasting, not
by a system. A `<script module>` or `$lib/tokens.js` constants file (or
CSS custom properties, same mechanism, just named as a scale) fixes that
structurally:

```css
:root {
  --space-1: .25rem; --space-2: .5rem; --space-3: .75rem;
  --space-4: 1rem;   --space-5: 1.5rem; --space-6: 2rem;
  --text-xs: .74rem; --text-sm: .84rem; --text-base: .95rem;
  --text-lg: 1.1rem; --text-xl: 1.4rem;
  --tap-min: 2.25rem; /* WCAG 2.5.5-ish minimum interactive target */
}
```

Every component built from these instead of a fresh guess each time is
what "less cramped" actually means as an enforceable rule, not a vibe —
concretely: form fields get `--space-3` vertical padding (12px, splitting
the difference between MD3's 16px-too-much and the current ad hoc
`.5rem`/8px-in-some-places-too-little), table rows get `--space-3` not
`.55rem` by coincidence, dialog content gets `--space-4` gap not whatever a
given page typed in `style=`.

### Component strategy: drop Material Web, not Svelte-native

This is the fork the brief calls out explicitly — argued, not dodged.

**Considered: keep `@material/web` inside Svelte.** Technically possible —
Material Web is Lit-based, framework-agnostic web components, and Svelte
can host arbitrary custom elements (`<md-outlined-text-field>` works as a
Svelte template node same as any HTML tag). **Rejected.** Three reasons:

1. **The whole reason [v3/15](../v3/15-design-system.md) adopted it —
   "the value here is as much in its interaction behavior... as in its
   visual tokens"** — stops being the deciding factor once the app has a
   real component framework of its own. Svelte's own component model
   (props, slots, reactive state, transitions) gives the same "don't
   hand-roll interaction behavior" benefit MD3 was adopted for, without a
   second, incompatible reactivity system layered underneath (Lit's
   reactive properties + Svelte's runes/stores means two different
   "when does this re-render" models in one app).
2. **The field-density bug is structural, not a config oversight.** MD3
   web components carry their own shadow-DOM-encapsulated default styling
   that a host app can only override through the specific custom properties
   each component happens to expose ([v3/15](../v3/15-design-system.md)
   documents two separate token namespaces already needed just for
   text-field vs. select sizing, plus a `min-width: 210px` with *no*
   exposed override hook at all, needing a blunt `min-width: 0 !important`-
   style CSS fight to defeat). A Svelte-native component owns its own
   markup — there's no shadow DOM to reach through, no vendor default to
   fight, no "which of these twelve `--md-outlined-select-text-field-*`
   variables actually controls padding" archaeology.
3. **Bundle size, concretely measured on this app today.** The current
   Vite build (`static/dist/`) has an unresolved chunk-splitting issue
   where Rollup's default (no `manualChunks` configured) non-deterministically
   assigns a large shared MD3+Lit runtime chunk to whichever page's entry
   happens to pull it in first — observed shipping as 135KB (28KB gzipped)
   attached to `coach.html`, a page whose own source is two lines that
   import nothing but a password-toggle helper. That's not a page-specific
   bug; it's the cost of a Lit runtime plus a component library riding
   along with pages that use almost none of it. Svelte's compiler emits
   only the DOM-manipulation code a component's actual template needs, no
   shared runtime of comparable size to carry.

**What replaces MD3, concretely:** a `$lib/components/` set, each a plain
`.svelte` file, built once and used everywhere — this list maps directly to
[v3/17's "Component needs, summarized"](../v3/17-full-app-redesign.md#component-needs-summarized)
plus what MD3 was standing in for:

| Component | Replaces |
|---|---|
| `Button.svelte` (variants: filled/outlined/text/ghost/danger) | `md-filled-button` etc. + `.btn`'s CSS |
| `TextField.svelte`, `Select.svelte` | `md-outlined-text-field`, `md-outlined-select` |
| `Dialog.svelte` | `md-dialog` (native `<dialog>` element under the hood — real focus trap, `Esc`-to-close, and `::backdrop` styling for free, zero dependency) |
| `Tabs.svelte` | `md-tabs`/`md-primary-tab` *and* the two remaining hand-rolled idioms ([v3/17 X2](../v3/17-full-app-redesign.md#x2--medium-three-tab-idioms-one-md3-component-that-should-replace-all-of-them)) — one implementation, not three |
| `DataTable.svelte` | `.data-table`'s currently-duplicated markup+sort-wiring (`wireSortableHeaders()`/`sortRows()` in `shared.js` become the component's internal logic, not a helper every page calls the same way by convention) |
| `Chip.svelte`, `Toast.svelte`, `Snackbar.svelte` | `.chip`, `shared.js`'s `toast()`, `md-snackbar` (the [live agent toast](../v3/15-design-system.md#live-agent-toast)) |
| `Sidebar.svelte`, `AppTopbar.svelte` | the ~24-times-pasted sidebar/topbar markup — one component, portal-aware nav list as a prop |
| `Checklist.svelte`, `StepMarker.svelte` | the first-run checklist ([v3/17 X4](../v3/17-full-app-redesign.md#x4--medium-onboarding-is-individually-good-empty-states-with-no-cross-page-checklist)) and `.step` |

Accessibility is the one place this trade needs an explicit commitment,
since it's the one place MD3 gave real defaults for free: every replacement
component must ship correct ARIA and keyboard handling matching what MD3
provided — `Dialog.svelte` on native `<dialog>` gets focus-trap/`Esc` for
free from the platform; `Tabs.svelte` needs its own `role="tab"`/
`aria-selected`/arrow-key navigation implemented once, deliberately, rather
than the "sometimes has it, sometimes doesn't" state
[v3/17 PRAC2](../v3/17-full-app-redesign.md#prac2--low-three-different-hand-rolled-tab-idioms-now-exist-none-of-them-md-tabs)
found across the three current tab implementations.

## Information architecture: file-based routing over the existing four portals

SvelteKit's `src/routes/` maps directly onto the app's existing IA
([v3/01](../v3/01-overview.md#the-four-applications)) — this rewrite
doesn't restructure *what* pages exist or how they connect, only what
they're built from. Route groups (SvelteKit's `(group)` folders, which
don't affect the URL) separate the four portals' shared layouts without
changing a single URL a bookmark or the backend's redirect logic
(`app/auth.py`'s post-login `LANDING` map in `login.html`, soon
`+page.svelte`) depends on:

```
src/routes/
├── (public)/                     # static/public/*.html, static/index.html's public-facing bits
│   ├── +layout.svelte            # Sidebar (public nav), no auth guard
│   ├── +page.svelte              # directory.html — now the site root, see below
│   ├── about/+page.svelte
│   ├── join/+page.svelte         # practitioner-signup.html
│   ├── join/submitted/+page.svelte
│   ├── signup/+page.svelte       # client-signup.html
│   ├── login/+page.svelte
│   ├── coach/[id]/+page.svelte
│   └── account/+page.svelte
├── (client)/client/
│   ├── +layout.svelte            # Sidebar (client nav) + auth guard (role=client)
│   ├── dashboard/+page.svelte
│   ├── questionnaire/+page.svelte
│   ├── files/+page.svelte
│   └── wearables/+page.svelte
├── (practitioner)/practitioner/
│   ├── +layout.svelte            # auth guard (role=practitioner)
│   ├── dashboard/+page.svelte
│   ├── clients/+page.svelte
│   ├── clients/[id]/+page.svelte
│   ├── consult/+page.svelte
│   ├── contacts/+page.svelte
│   ├── knowledge/+page.svelte
│   ├── profile/+page.svelte
│   └── upgrade/+page.svelte
└── (admin)/admin/
    ├── +layout.svelte            # auth guard (role=admin)
    ├── +page.svelte              # static/index.html, the knowledge dashboard — kept at /admin
    ├── dashboard/+page.svelte
    ├── users/+page.svelte
    └── questionnaires/+page.svelte
```

One deliberate IA change, both grounded in existing findings rather than
invented: **`directory.html` becomes the site root (`/`)**, not a page
reached via nav — [v3/17 PUB5](../v3/17-full-app-redesign.md#pub5--low-the-directory-and-about-page-have-no-visual-identity-beyond-the-card-grid)
already named the directory as *"the product whose entire public-facing job
is to get a visitor to pick a practitioner"* and the least-considered page
in the product; making it the landing page instead of `/about` (today's
actual root per `about.html`'s `active` sidebar link, confirmed against
[v3/03](../v3/03-website.md)) puts the golden-path-2 entry point where a
visitor actually lands, matching how `03-website.md`'s own practitioner
directory section frames it as the primary discovery surface. `/about`
stays a page, just not the root.

Auth guards (`+layout.ts`'s universal `load()` calling a
`requireRole`-equivalent against the FastAPI session) replace `shared.js`'s
client-side `requireRole('admin')`/etc. pattern. Worth being precise about
what this actually improves, now that the static adapter (not adapter-node)
is the target: it's **not** the "redirect before any markup reaches the
browser" guarantee true SSR would give — the client/practitioner/admin
portals are CSR-only, so the same static app shell always loads first,
same as today. What it *does* improve: `load()` in a `+layout.ts` blocks
that route's content from rendering until the role check resolves, so an
unauthorized visitor sees a loading state, never a flash of the actual
protected page's shell before the redirect fires — the flash `shared.js`'s
current post-paint check produces. A smaller, honest win, not the bigger
one SSR would have bought.

## Data layer: `load()` functions against the unchanged FastAPI API

**FastAPI's JSON contract does not change.** Every route in
[v3/08-api.md](../v3/08-api.md) stays exactly as documented — same paths,
same auth dependencies (`app/auth.py`'s `require_admin`/
`require_pro_practitioner`/etc.), same request/response shapes. This
rewrite is a client swap, not an API redesign.

**Cookie handling stays exactly as simple as it is today.**
`app/auth.py`'s session cookie is `httponly, samesite=lax, secure=$COOKIE_SECURE`
([app/auth.py:120-122](../../app/auth.py)) — invisible to browser JS by
design, unaffected by this rewrite. The static-adapter target means every
`load()` in the client/practitioner/admin portals runs **in the browser**
(a universal `+layout.ts`/`+page.ts`, not a `.server.ts`), so the browser
attaches the cookie to the request automatically, exactly like `shared.js`'s
`api()` helper does today — no cookie-forwarding wrinkle to design around,
because there's no server-side request in this rewrite's version of the
data layer at all. (This is the concrete mechanical simplification the
static-adapter decision above buys, beyond just removing the memory risk.)

```ts
// src/routes/(practitioner)/dashboard/+layout.ts — runs client-side
export async function load({ fetch }) {
  const res = await fetch(`${env.PUBLIC_API_BASE}/api/me/profile`);
  if (res.status === 401) throw redirect(303, '/login');
  return { profile: await res.json() };
}
```

SvelteKit's `event.fetch` is still the one to use (not the raw global) —
under the static adapter it's mainly relevant for SSR'd/prerendered routes,
but using it consistently keeps every `load()` written the same way
regardless of which routes are prerendered vs. client-only. One
`$lib/api.ts` wrapper around it, reused by every `load()`, replaces
`shared.js`'s `api()` helper.

**The SSE consult stream** ([v3/08 §Live progress stream](../v3/08-api.md#live-progress-stream))
was always going to be client-side regardless of adapter choice — it's a
long-lived, user-initiated `POST` with a streaming response, not page data,
so it was never going through `load()` in the first place. Stays a
client-side `fetch()` with a `ReadableStream` reader, exactly as
[v3/08](../v3/08-api.md#live-progress-stream) already specifies for
`shared.js` today — a `$lib/consultStream.ts` module a Svelte component
calls from an event handler (button click), same shape as today's plain-JS
version, just typed and componentized.

**Error handling**: FastAPI's existing 401/403/404/502 responses
([v3/08 §Failure modes](../v3/08-api.md#failure-modes)) map to SvelteKit's
`error()`/`redirect()` helpers inside `load()` for page-level failures, and
to the same `toast()`-equivalent pattern for in-page action failures
(create/update/delete calls staying client-side, same as today) — no new
failure modes invented, just relocated to SvelteKit's idioms.

## Deployment: static adapter, FastAPI keeps serving it

Originally specced as adapter-node with a new Node server process; revised
after the memory math below made the tradeoff explicit (see the note at
the top of this document). This version of the section is what's actually
recommended.

### The memory question this used to raise, and why it's now moot

Per `DEPLOY.md`: **1.9 GB total RAM**, Neo4j's JVM the bulk of it, FastAPI/
uvicorn capped at `MemoryMax=500M`, leaving **~500-700 MB available at
steady state** — DEPLOY.md's own words: *"there is no headroom for a
second JVM or a large concurrent load."* Adapter-node would have added a
second long-running server process into that headroom, estimated (not
measured) at 150-300MB under real traffic — "fits, barely, no margin,"
and the one part of that version of this plan that could have become a
production incident rather than a design regret. **The static adapter has
no server process to add.** `npm run build` produces plain HTML/JS/CSS —
the public portal's routes pre-rendered at build time, everything else a
client-side bundle — synced to `/opt/clinic/static` and served by the
exact same FastAPI static mount that serves `static/dist/` today. The VPS's
memory budget is untouched by this rewrite, full stop; no resize to budget
for, no new systemd unit whose OOM risk needs a `MemoryMax` ceiling.

### Process topology

```
Cloudflare (Full mode, unchanged)
  → nginx :443/:80 (unchanged: self-signed origin-tls, client_max_body_size 25m,
                     proxy_read_timeout 300s — clinic-proxy.conf, unchanged)
      → FastAPI/uvicorn on 127.0.0.1:8000 (unchanged `clinic` systemd unit)
          → serves /api/* (unchanged)
          → serves the SvelteKit build's static output from its existing
            /static mount (prerendered HTML for the public portal,
            the client-side bundle + its own thin HTML shell for
            client/practitioner/admin)
```

One process, one systemd unit, same as today — this rewrite changes what's
*inside* `/opt/clinic/static`, not how many things run on the box.

### Build/deploy pipeline

Adds one stage to what [v3/11 §Build step](../v3/11-operations.md#build-step)
already documents (Vite building `static/dist/`): `npm run build` inside
the SvelteKit project (using `@sveltejs/adapter-static`) produces `build/`
— a directory of prerendered HTML for `(public)` routes and a
client-side-rendered SPA shell for the rest — synced into
`/opt/clinic/static` the same way `static/dist/` is synced today, no new
`systemctl` unit to restart. `svelte.config.js` sets
`kit.adapter = adapter-static` with `fallback: 'app.html'` (the SPA shell
non-prerendered routes hydrate into) and each `(public)` route exports
`export const prerender = true`; everything under `(client)`/
`(practitioner)`/`(admin)` exports `export const ssr = false` (no
prerendering attempted for routes that require auth and would just 401 at
build time anyway).

## Migration/cutover plan

**This is a live production app**, even though current real-user data is
near-zero (0 practitioners as of the last production check this session) —
the domain, TLS, and Cloudflare setup are real and already serving traffic
checks. A big-bang cutover (build the whole SvelteKit app, flip DNS/nginx
one day) is the highest-risk option and not recommended.

**Recommended: parallel deploy on a path prefix, page-by-page promotion,
same spirit as [v3/15](../v3/15-design-system.md#migration-approach)'s own
"page by page, not a big-bang rewrite" MD3 migration approach** — this
project has already done an incremental frontend migration once and it
worked (per [v3/17](../v3/17-full-app-redesign.md)'s own retrospective:
*"this app already went through two real redesign passes and it shows"*).
Concretely:

1. Build the SvelteKit app against a local/staging copy of the FastAPI
   backend first — verify the whole route tree, every auth-guarded portal,
   and the SSE consult stream work before either build ever reaches the
   production VPS.
2. Sync the build's output into `/opt/clinic/static` under a **separate
   path prefix first** (e.g. `/opt/clinic/static/v4/`), not overwriting
   today's files — reachable at a throwaway URL
   (`telehealth.devshorepartners.id/v4/about`) for a final production-data
   smoke test that doesn't touch what real visitors see.
3. Promote one portal at a time (public → client → practitioner → admin,
   roughly ascending order of how much a bug would cost — admin last since
   an admin-portal regression blocks the operator, not a visitor) by
   replacing that portal's files in the real `static/` paths and verifying
   in production, same "page by page, not big-bang" spirit
   [v3/15](../v3/15-design-system.md#migration-approach)'s own MD3
   migration already used successfully on this exact app. No nginx changes
   at any step — FastAPI's static mount doesn't care whether a file under
   `static/practitioner/dashboard.html` was hand-written or built by Vite
   or built by SvelteKit, only that the path resolves.
4. Once every portal is promoted, archive (don't delete) the old
   `static/*.html` and `src/pages/*.js` files — the same "keep the record,
   don't just delete" instinct [v3/README.md](../v3/README.md) already
   applies to superseded spec versions.

**What "spec only, not yet implemented" leaves as open engineering risk,
stated plainly**: this plan is not yet built or tested against the real
backend, and the auth-guard client-side-redirect behavior needs to be
verified against every one of `app/auth.py`'s actual role-check edge cases
(not just the happy path) — a wrong redirect on an edge case (e.g. a
suspended practitioner, a role that changed mid-session) is the realistic
failure mode here, not an outage; there's no nginx routing risk to verify
in this version of the plan, since nothing about nginx changes.

## Explicit non-goals

- **Backend, data model, or API contract changes** — [v3/08](../v3/08-api.md)
  stands unchanged; this is a client-only rewrite.
- **Product scope changes** — no booking/scheduling/telehealth/video,
  unchanged from [v3/01](../v3/01-overview.md#out-of-scope--deliberately).
- **A visual redesign** — the gradient/glass/botanical identity is kept
  literally, not reinterpreted; what changes is density (fixed structurally)
  and what the identity is built out of (Svelte components + plain CSS
  custom properties instead of MD3 web components).
- **The four-portal IA** — one deliberate exception (`directory.html` as
  site root, [§Information architecture](#information-architecture-file-based-routing-over-the-existing-four-portals)),
  everything else routes exactly where it does today.
- **SSR for the SSE consult stream** — stays client-side, see
  [§Data layer](#data-layer-load-functions-against-the-unchanged-fastapi-api).
- **A VPS resize** — no longer needed. The earlier adapter-node version of
  this document flagged one as a real recommendation; the static-adapter
  target removes the reason for it entirely, see
  [§Deployment](#deployment-static-adapter-fastapi-keeps-serving-it).
