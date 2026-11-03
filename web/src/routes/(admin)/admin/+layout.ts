import { redirect } from '@sveltejs/kit';
import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const session = await get(fetch, '/auth/me').catch(() => null);
	if (!session || session.role !== 'admin') throw redirect(303, '/login');
	// Loaded here, not just on the dashboard page, so the footer status
	// bar (+layout.svelte) has something to show on every admin screen,
	// not only /admin/dashboard.
	const health = await get(fetch, '/health').catch(() => null);
	return { session, health };
}
