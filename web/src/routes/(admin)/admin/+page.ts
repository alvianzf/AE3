import { get } from '$lib/api';

export const ssr = false;

// The admin portal's Home launcher (see +page.svelte) — replaces both
// the old Library-as-root and the old separate Dashboard page. Live
// tile status still needs the site stats; the AI-provider toggle moved
// to its own /admin/settings page (a tile here, not a thing every page
// load has to carry).
export async function load({ fetch }) {
	const stats = await get(fetch, '/admin/stats').catch(() => ({}));
	return { stats };
}
