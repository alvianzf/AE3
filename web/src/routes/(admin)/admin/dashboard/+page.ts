import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const stats = await get(fetch, '/admin/stats').catch(() => ({}));
	return { stats };
}
