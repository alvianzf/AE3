import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const session = await get(fetch, '/auth/me').catch(() => null);
	return { session };
}
