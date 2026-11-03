import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch, params, url }) {
	// Caught, not left to throw into SvelteKit's generic error boundary —
	// the page itself shows a clear "couldn't load" state instead.
	const source = await get(fetch, `/sources/${params.id}/text`).catch((err) => ({ error: err.message }));
	return { source, locator: url.searchParams.get('locator') ?? '' };
}
