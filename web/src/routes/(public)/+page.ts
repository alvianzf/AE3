// specs/v4.1/01 — the root is now a static, information-first landing page
// (formerly the practitioner directory, moved to /practitioners; formerly
// this route's own content lived at /about, now merged in here). No live
// data on this page, so no fetch — just a prerendered marketing page.
export const prerender = true;
