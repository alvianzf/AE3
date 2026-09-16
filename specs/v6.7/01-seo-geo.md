# v6.7/01 — SEO and GEO for the public pages

**Status: implemented, live-verified in production.**

Every public page (`web/src/routes/(public)/*`) had only a bare `<title>`
— no meta description, no canonical, no Open Graph/Twitter tags, no
structured data, no sitemap, no robots.txt beyond a blanket allow, no
llms.txt.

## What shipped

- **`Seo.svelte`** (`web/src/lib/components/`) — shared title/description/
  canonical/OG/Twitter-card component, wired into every public page.
  Content pages (landing, practitioner directory, coach profiles, join)
  get real per-page descriptions and are indexable; pure utility pages
  (login, signup, account, join/submitted) are `noindex` — they carry no
  content worth ranking.
- **JSON-LD structured data**: `Organization` schema on the landing page;
  per-practitioner `Person` schema (name, bio-derived description,
  specialties as `knowsAbout`, languages as `knowsLanguage`) on each
  coach profile.
- **`og-image.png`** — a branded 1200×630 image matching the existing
  hero gradient/wordmark, rendered via a one-off Playwright screenshot of
  a static HTML page (not a new runtime dependency — Playwright was
  already in `requirements.txt` for the scraper's headless-browser
  fallback, `v6.5`).
- **`sitemap.xml`** (`web/src/routes/sitemap.xml/+server.ts`) —
  prerendered at build time like every other public route
  (`svelte.config.js`'s adapter-static), enumerating the static paths
  plus every practitioner via the same `/api/practitioners` fetch
  `coach/[id]`'s own `entries()` already makes.
- **`robots.txt`** — explicitly name-allows the major AI answer-engine
  crawlers (GPTBot, ChatGPT-User, ClaudeBot, Claude-User, anthropic-ai,
  PerplexityBot, Google-Extended, CCBot). The existing blanket `Disallow:`
  already permitted them; naming them is the convention these crawlers
  themselves look for. Links the new sitemap.
- **`llms.txt`** (static, per the llmstxt.org convention) — a
  plain-language summary of what Clinic is, who it's for, how the
  grounded/cited/checked answer pipeline works, and an explicit note that
  authenticated portal pages are out of scope for crawling.
- **`PUBLIC_SITE_URL`** — new env var for the absolute origin canonical/
  OG/sitemap need (unlike `PUBLIC_API_BASE`, deliberately relative in
  production). Added to `web/.env.example` and both the `check` and
  `build` steps in `.github/workflows/deploy.yml`.

## A real bug found and fixed the same day

`app/main.py`'s `_WEB_ROOT_FILES` is an explicit allowlist for root-level
static files the SPA-fallback route serves as-is (`robots.txt`, a
favicon). The new `sitemap.xml`, `llms.txt`, and `og-image.png` weren't
on it, so all three silently fell through to the SPA shell — a 200
response, but with `app.html`'s contents, not their real content.
Confirmed live on production before the fix (`curl .../sitemap.xml`
returned HTML). Fixed by adding the three filenames to the allowlist.

## Verification

`npm run check` clean. `npm run build` succeeds and produces
`sitemap.xml`/`robots.txt`/`llms.txt`/`og-image.png` in the output, with
correct meta/OG/JSON-LD/`noindex` tags confirmed by inspecting the built
HTML. Re-verified live on production after the root-files fix: all four
endpoints return their real content, not the SPA shell.
