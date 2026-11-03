import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch, params, url }) {
	// Caught, not left to throw into SvelteKit's generic error boundary —
	// the page itself shows a clear "couldn't load" state instead (found
	// live: a failed fetch here previously left no useful signal for why
	// the detail page came up empty).
	const source = await get(fetch, `/sources/${params.id}/text`).catch((err) => ({ error: err.message }));
	return { source, locator: url.searchParams.get('locator') ?? '' };
}
