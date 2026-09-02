// Thin wrapper around event.fetch, replacing shared.js's api() helper.
// Cookie auth is automatic (httponly session cookie, browser attaches it) —
// see specs/v4/01-sveltekit-frontend.md#data-layer.
//
// In production PUBLIC_API_BASE is '' (relative /api/... — FastAPI serves
// the build from the same origin, per specs/v4/01-sveltekit-frontend.md's
// deployment section). Locally, `npm run build`'s prerender step runs in
// Node (no CORS, but no relative-URL resolution either) against a real
// backend, while the browser needs same-origin (proxied by vite's dev/
// preview server — see vite.config.ts) since there's no CORS middleware on
// the FastAPI app to relax. `building` (true only during the Node-side
// build step) picks the right one automatically.
import { building } from '$app/environment';
import { PUBLIC_API_BASE, PUBLIC_API_BASE_BUILD } from '$env/static/public';

const apiBase = building ? PUBLIC_API_BASE_BUILD || PUBLIC_API_BASE : PUBLIC_API_BASE;

export class ApiError extends Error {
	status: number;
	detail: unknown;
	constructor(message: string, status: number, detail: unknown) {
		super(message);
		this.status = status;
		this.detail = detail;
	}
}

export async function api(
	fetchFn: typeof fetch,
	path: string,
	opts: RequestInit = {}
): Promise<any> {
	// During the build's prerender step, SvelteKit's `event.fetch` enforces
	// browser-style CORS even though it's running in Node — real for a
	// cross-origin absolute URL like PUBLIC_API_BASE_BUILD, since there's no
	// CORS middleware on FastAPI (matches production, which never needs one:
	// same origin there). Plain global fetch has no such restriction and
	// prerendering doesn't need cookies anyway (every prerendered route here
	// is public), so use it directly at build time.
	const doFetch = building ? fetch : fetchFn;
	const res = await doFetch(`${apiBase}/api${path}`, {
		credentials: 'include',
		...opts
	});
	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		const d = body.detail;
		const message = (d && typeof d === 'object' ? d.message : d) || res.statusText;
		throw new ApiError(message, res.status, d);
	}
	if (res.status === 204) return null;
	return res.json().catch(() => null);
}

export const json = (method: string, body: unknown): RequestInit => ({
	method,
	headers: { 'Content-Type': 'application/json' },
	body: JSON.stringify(body)
});

export const get = (fetchFn: typeof fetch, path: string) => api(fetchFn, path);
export const post = (fetchFn: typeof fetch, path: string, body?: unknown) =>
	api(fetchFn, path, body !== undefined ? json('POST', body) : { method: 'POST' });
export const put = (fetchFn: typeof fetch, path: string, body?: unknown) =>
	api(fetchFn, path, json('PUT', body));
export const del = (fetchFn: typeof fetch, path: string) => api(fetchFn, path, { method: 'DELETE' });
