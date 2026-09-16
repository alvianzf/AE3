import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [stats, health] = await Promise.all([
		get(fetch, '/admin/stats').catch(() => ({})),
		get(fetch, '/health').catch(() => null)
	]);
	return { stats, health };
}
