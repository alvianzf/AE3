// Explicit opt-in, not relying on crawl-discovery: this page has no
// prerender directive of its own, and PublicNav/PublicFooter (the FHC
// one-page rebrand) no longer link to it, so adapter-static's default
// crawl-from-'/' never reached it and silently skipped writing its HTML
// — non-JS clients (including the GEO crawlers robots.txt allows) got a
// blank app shell instead of this page's content.
export const prerender = true;
