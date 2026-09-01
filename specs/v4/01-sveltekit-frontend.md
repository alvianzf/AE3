# 01 · Frontend rewrite: SvelteKit

Requested directly: "as a really world level UI UX designer, tear down the
app, build a new FE that is better, more user friendly, less cramped, and
much better while keeping the gradient color since user love it... write it
in Sveltekit." Confirmed via follow-up: **adapter-node** (real SSR, a new
Node process in production — not the static-adapter option that would have
kept today's "Vite output served by FastAPI's static mount" deploy shape
unchanged), and **spec only** right now — no code, nothing touches
production until this is reviewed.

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

Auth guards (`+layout.server.ts`'s `load()` calling `requireRole`-equivalent
against the FastAPI session) replace `shared.js`'s client-side
`requireRole('admin')`/etc. pattern — this is a *strictly better* version
of the same check, not a new one: today's guard runs after the page has
already painted (a flash of the page's shell before the redirect fires,
visible on a slow connection), SSR-side guard redirects before any markup
reaches the browser.

## Data layer: `load()` functions against the unchanged FastAPI API

**FastAPI's JSON contract does not change.** Every route in
[v3/08-api.md](../v3/08-api.md) stays exactly as documented — same paths,
same auth dependencies (`app/auth.py`'s `require_admin`/
`require_pro_practitioner`/etc.), same request/response shapes. This
rewrite is a client swap, not an API redesign.

**Cookie forwarding, the one real mechanical wrinkle of adapter-node SSR.**
`app/auth.py`'s session cookie is `httponly, samesite=lax, secure=$COOKIE_SECURE`
([app/auth.py:120-122](../../app/auth.py)) — invisible to browser JS by
design, which is correct and unaffected by this rewrite. What changes is
*who* needs to read it: today, every fetch is client-side, so the browser
attaches the cookie automatically. Under adapter-node SSR, a page's
`load()` function runs **on the SvelteKit Node server**, which needs to
explicitly forward the incoming request's `Cookie` header to its own call
to FastAPI:

```ts
// src/routes/(practitioner)/dashboard/+page.server.ts
export async function load({ fetch, cookies }) {
  const res = await fetch(`${env.API_BASE}/api/me/profile`, {
    headers: { cookie: `clinic_session=${cookies.get('clinic_session')}` }
  });
  if (res.status === 401) throw redirect(303, '/login');
  return { profile: await res.json() };
}
```

SvelteKit's `event.fetch` (not the global `fetch`) is required here — it's
the version that participates in SvelteKit's SSR request lifecycle and
correctly handles relative URLs against the internal API origin. This
pattern is one hook (`src/hooks.server.ts`, or a `$lib/server/api.ts`
wrapper) written once and reused by every `load()`, not fifty ad hoc cookie
reads.

**The SSE consult stream** ([v3/08 §Live progress stream](../v3/08-api.md#live-progress-stream))
is the one endpoint that can't go through a `load()` function at all —
it's a long-lived, user-initiated `POST` with a streaming response, not
page data. It stays a client-side `fetch()` with a `ReadableStream` reader,
exactly as [v3/08](../v3/08-api.md#live-progress-stream) already specifies
for `shared.js` today — this becomes a `$lib/consultStream.ts` module a
Svelte component calls from an event handler (button click), same shape as
today's plain-JS version, just typed and componentized. Runs in the
browser either way; adapter-node's SSR doesn't touch it.

**Error handling**: FastAPI's existing 401/403/404/502 responses
([v3/08 §Failure modes](../v3/08-api.md#failure-modes)) map to SvelteKit's
`error()`/`redirect()` helpers inside `load()` for page-level failures, and
to the same `toast()`-equivalent pattern for in-page action failures
(create/update/delete calls staying client-side, same as today) — no new
failure modes invented, just relocated to SvelteKit's idioms.

## Deployment: adapter-node alongside the existing FastAPI process

This is the section with the most concrete, checkable numbers, because it's
the one part of this proposal that's wrong if it ignores the box it has to
run on.

### What the VPS actually has today

Per `DEPLOY.md`: **1.9 GB total RAM**, Neo4j's JVM the bulk of it (heap
512m + pagecache 256m, `/etc/neo4j/neo4j.conf`), FastAPI/uvicorn capped at
`MemoryMax=500M` (the `clinic` systemd unit), leaving **~500-700 MB
available at steady state** — DEPLOY.md's own words: *"there is no headroom
for a second JVM or a large concurrent load."* A Node SvelteKit adapter-node
process is not a JVM, but it is a second long-running server process with
its own baseline (a minimal SvelteKit adapter-node app idles around
60-100MB RSS; under concurrent SSR requests — several `load()` calls each
holding a FastAPI round-trip open — that climbs, plausibly into the
150-300MB range under real traffic, though this hasn't been load-tested
against this specific app's `load()` fan-out).

**Honest read: this fits, barely, with no margin for anything else.**
500-700MB available today, a SvelteKit process eating an estimated
150-300MB under load, leaves 200-550MB — enough to not immediately OOM, not
enough to add a third thing (a Redis cache, a second Node worker for
zero-downtime deploys, headroom for a Neo4j heap bump if the library
grows past today's 10-20-practitioner sizing). **The honest answer, not
dodged: budget for a VPS resize before or immediately after this ships** —
even a bump to 4GB total removes the "barely fits" risk entirely for a
cost that's noise next to the engineering time this rewrite already costs.
Shipping adapter-node on the current 1.9GB box without a resize is the one
part of this plan that could turn into a production incident (OOM-killed
Node process under a traffic spike) rather than a design regret.

### Process topology

```
Cloudflare (Full mode, unchanged)
  → nginx :443/:80 (unchanged: self-signed origin-tls, client_max_body_size 25m,
                     proxy_read_timeout 300s — clinic-proxy.conf, unchanged)
      → SvelteKit (adapter-node) on 127.0.0.1:3000, new systemd unit `clinic-web`
          → proxies /api/* internally to FastAPI on 127.0.0.1:8000 (unchanged `clinic` unit)
      OR
      → FastAPI directly on /api/* (nginx-level split, bypassing SvelteKit for API calls)
```

**Recommendation: nginx splits at the edge, not SvelteKit proxying
internally.** Two reasons: (1) it means a `/api/*` request never pays for a
hop through the Node process at all — one less thing in the request path
for the majority of traffic once the SPA has hydrated and is calling the
API directly from the browser (post-hydration, most calls are plain
client-side `fetch()`, not `load()`-driven SSR — only the *first* page load
of a session goes through SSR `load()`, which is the only place the
Node-process-proxies-to-FastAPI question matters at all); (2) it keeps
nginx as the one place routing decisions live, matching how `DEPLOY.md`
already documents the Cloudflare-real-IP and TLS setup as nginx's job, not
an app-level concern. Concretely, one new `location /api/ { proxy_pass
http://127.0.0.1:8000; }` block added to the existing `clinic` nginx site
config, alongside a new `location / { proxy_pass http://127.0.0.1:3000;
}` for everything SvelteKit serves.

New systemd unit (`/etc/systemd/system/clinic-web.service`), same shape as
the existing `clinic` unit:

```ini
[Unit]
Description=Clinic SvelteKit frontend
After=network.target clinic.service
[Service]
Type=simple
User=clinic
WorkingDirectory=/opt/clinic-web
ExecStart=/usr/bin/node build/index.js
Environment=PORT=3000
Environment=API_BASE=http://127.0.0.1:8000
MemoryMax=300M
Restart=on-failure
[Install]
WantedBy=multi-user.target
```

`MemoryMax=300M` mirrors the existing `clinic` unit's own self-imposed cap
(`500M`) — a ceiling, not a request; systemd kills the process on breach
rather than letting an unbounded Node process take down Neo4j by memory
pressure, same protective reasoning the existing unit already applies to
uvicorn.

### Build/deploy pipeline

Adds one stage to what [v3/11 §Build step](../v3/11-operations.md#build-step)
already documents (Vite building `static/dist/`): `npm run build` inside
the SvelteKit project produces `build/` (adapter-node's output, a
standalone Node app), synced to `/opt/clinic-web` the same way `static/`
and `src/` are synced to `/opt/clinic` today, then `systemctl restart
clinic-web` alongside the existing `systemctl restart clinic`. No change to
how FastAPI itself deploys.

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

1. Stand up `clinic-web` on the VPS listening on `127.0.0.1:3000`, **not**
   yet reachable from nginx — build and verify the whole route tree against
   the real FastAPI backend from a local machine or a staging subdomain
   first, not the production edge.
2. Add an nginx path-based split for one low-traffic, low-risk route first
   (`/about` is the obvious first candidate — static content, no auth, no
   forms) — `location = /about { proxy_pass http://127.0.0.1:3000; }`
   ahead of the general `location / { proxy_pass http://127.0.0.1:8000/static/...; }`
   fallback that still serves every other page from the current stack.
3. Promote one portal at a time (public → client → practitioner → admin,
   roughly ascending order of how much a bug would cost — admin last since
   an admin-portal regression blocks the operator, not a visitor), each
   verified in production behind its own nginx `location` block before the
   next moves.
4. Once every route is proxied to `clinic-web`, delete the old `location`
   fallbacks and, separately, archive (don't delete) `static/*.html` and
   `src/pages/*.js` — the same "keep the record, don't just delete"
   instinct [v3/README.md](../v3/README.md) already applies to superseded
   spec versions.

**What "spec only, not yet implemented" leaves as open engineering risk,
stated plainly**: this plan is not load-tested, the per-`load()`-call
memory estimate above is an estimate not a measurement, the auth-guard
SSR-redirect behavior needs to be verified against every one of
`app/auth.py`'s actual role-check edge cases (not just the happy path), and
the nginx path-split approach needs the exact `location` block precedence
verified against the *existing* `clinic-proxy.conf` shared snippet (a
misordered `location` block silently serving the wrong app for a path is
the realistic failure mode of step 2-3 above, not a dramatic outage).

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
- **A VPS resize decision** — flagged as a real, concrete recommendation
  in [§Deployment](#deployment-adapter-node-alongside-the-existing-fastapi-process),
  but the actual sizing/cost call belongs to whoever owns the
  infrastructure budget, not this document.
