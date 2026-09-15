"""Fetches a URL's HTML and strips it to visible text, cheaply, before an
LLM ever sees it (specs/v3/18-document-ingest-upgrade.md Component 2).
urllib.request + html.parser for the common case (a normal server-
rendered page) — same convention this app already uses for PDF
extraction: a blocking call in a plain synchronous route, which
FastAPI's threadpool handles like any other. Falls back to a real
headless browser (Playwright, specs/v6.5/04) only when that fails: a
bot-challenge block (Cloudflare and similar return a 401/403/429 to a
plain HTTP client but pass a real browser that executes JS) or a page
that returns 200 with no visible text (a JS-only SPA — urllib never
executes anything, so client-rendered content is invisible to it).

This is NOT the real "discard chrome, keep content" extraction — that's
llm.extract_article(), a separate LLM call. This step only exists to cut
token cost and obvious noise (script/style tags and their contents)
before the real extraction runs; a <div class="sidebar-links"> styled to
look like navigation still reaches the LLM, deliberately — recognizing
that needs judgment a tag-based selector can't make, which is exactly
why the LLM step exists at all.
"""
from __future__ import annotations

import urllib.error
import urllib.request
from html.parser import HTMLParser

from fastapi import HTTPException

_DROP_TAGS = {"script", "style", "nav", "header", "footer"}
_MAX_FETCH_BYTES = 5 * 1024 * 1024  # a page worth scraping is never legitimately huge
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
# Status codes worth retrying with a real browser rather than failing
# outright — a bot-challenge block, not "the URL is actually wrong"
# (a 404/500 gets no fallback; a slower, heavier browser fetch won't fix
# a page that doesn't exist).
_BOT_BLOCK_CODES = {401, 403, 429}



# Cloudflare's own standard challenge-page title — checked after the wait
# below so a still-challenged page is never mistaken for real content.
# Confirmed live it's not even reliably solved: the automation-controlled
# fix below passed once, then failed the identical URL twice more shortly
# after (same site, same browser config) — Cloudflare's managed challenge
# has a risk-scoring element this app can't fully control, not a fixed
# pass/fail based on browser config alone.
_CHALLENGE_TITLE = "Just a moment..."


def _fetch_via_browser(url: str) -> str:
    """A real (headless) Chromium page load — executes JS, so it can pass
    a Cloudflare-style challenge a plain HTTP client can't, and renders a
    client-side SPA's actual content. Heavier and slower than the plain
    fetch above on purpose: this only runs when that already failed.

    Plain headless Chromium alone wasn't enough — confirmed live against
    a real Cloudflare-managed-challenge page (ifm.org, 2026-09-15): it
    still showed "Just a moment..." after 6+ seconds, meaning Cloudflare
    fingerprinted the browser itself as automated (the standard tell is
    `navigator.webdriver`, which Playwright sets true by default) and
    never let the challenge resolve, independent of the User-Agent
    string. `--disable-blink-features=AutomationControlled` plus
    overriding `navigator.webdriver` to `undefined` before any page
    script runs is a well-known, minimal fix for exactly this — but not
    a guaranteed one (see `_CHALLENGE_TITLE` above): this raises a clear
    error rather than silently returning the challenge page's own
    boilerplate as if it were the article, which it would do without
    this check — found live, the exact failure this app hit first."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise HTTPException(
            502, "Could not fetch that URL, and the headless-browser "
            "fallback isn't installed on this server."
        ) from exc
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
            try:
                page = browser.new_page(user_agent=_BROWSER_UA, viewport={"width": 1280, "height": 800})
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page.goto(url, timeout=20_000, wait_until="domcontentloaded")
                # A Cloudflare challenge resolves client-side a few seconds
                # after load, not instantly — domcontentloaded fires on the
                # challenge page itself, so give it a moment before reading
                # content. One retry-wait before giving up, since the first
                # few seconds' outcome isn't always final.
                page.wait_for_timeout(6_000)
                if page.title() == _CHALLENGE_TITLE:
                    page.wait_for_timeout(6_000)
                if page.title() == _CHALLENGE_TITLE:
                    raise HTTPException(
                        502, "That site's bot-protection challenge didn't clear, "
                        "even with a real browser. Try again shortly, or paste "
                        "the article text directly instead."
                    )
                html_text = page.content()
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise HTTPException(502, f"Could not fetch that URL, even with a real browser: {exc}") from exc
    return html_text


class _TextStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _DROP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in _DROP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.parts.append(stripped)


def _strip_text(html_text: str) -> str:
    if len(html_text.encode("utf-8", errors="replace")) > _MAX_FETCH_BYTES:
        raise HTTPException(400, "That page is too large to scrape.")
    stripper = _TextStripper()
    stripper.feed(html_text)
    return "\n".join(stripper.parts)


def fetch_and_strip(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "Enter a valid http(s) URL.")
    request = urllib.request.Request(url, headers={
        # A default urllib user agent gets an outright 403 from some sites.
        "User-Agent": "Mozilla/5.0 (compatible; ClinicLibraryBot/1.0)",
    })
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(_MAX_FETCH_BYTES + 1)
        text = _strip_text(raw.decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code not in _BOT_BLOCK_CODES:
            raise HTTPException(502, f"Could not fetch that URL: {exc}") from exc
        # Confirmed live, 2026-09-15: a real Cloudflare managed-challenge
        # block (Server: cloudflare, Cf-Mitigated: challenge) on a plain
        # User-Agent AND a real browser's User-Agent both — the block
        # isn't about what the request claims to be, it requires actually
        # executing the challenge's JS, which only a real browser can do.
        text = _strip_text(_fetch_via_browser(url))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, f"Could not fetch that URL: {exc}") from exc

    if not text.strip():
        # A 200 response with no visible text is a JS-only SPA — urllib
        # never executes anything, so client-rendered content doesn't
        # exist as far as it's concerned. One retry with a real browser
        # before giving up.
        text = _strip_text(_fetch_via_browser(url))
    if not text.strip():
        raise HTTPException(
            400,
            "No text content found on that page, even with a real browser "
            "— it may be behind a login, or genuinely has no article text.",
        )
    return text
