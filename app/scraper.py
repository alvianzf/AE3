"""Fetches a URL's HTML and strips it to visible text, cheaply, before an
LLM ever sees it (specs/v3/18-document-ingest-upgrade.md Component 2).
Stdlib only (urllib.request + html.parser) — no new dependency, same
convention this app already uses for PDF extraction: a blocking call in a
plain synchronous route, which FastAPI's threadpool handles like any other.

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
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, f"Could not fetch that URL: {exc}") from exc
    if len(raw) > _MAX_FETCH_BYTES:
        raise HTTPException(400, "That page is too large to scrape.")
    html_text = raw.decode("utf-8", errors="replace")
    stripper = _TextStripper()
    stripper.feed(html_text)
    text = "\n".join(stripper.parts)
    if not text.strip():
        # Known gap, stated plainly rather than failing silently: a JS-
        # rendered page (React/Vue with no server-rendered content) has no
        # text for urllib to see at all. A headless-browser fetch would
        # fix this but is a materially heavier dependency, not added here.
        raise HTTPException(
            400,
            "No text content found on that page — it may require "
            "JavaScript to render, which this scraper can't do.",
        )
    return text
