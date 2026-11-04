import { get } from '$lib/api';

// specs/v4.1/01 — the root is now a static, information-first landing page
// (formerly the practitioner directory, moved to /practitioners; formerly
// this route's own content lived at /about, now merged in here).
export const prerender = true;

// specs/v8 §8.1 — the "available practitioners" highlight needs live
// practitioner data (same prerender-then-refresh pattern as /practitioners'
// own loader: fast, SEO-able first paint from the build-time snapshot, a
// client-side refresh after hydration since approvals/opt-ins happen at
// any time).
export async function load({ fetch }) {
	const practitioners = await get(fetch, '/practitioners').catch(() => []);
	return { practitioners };
}
