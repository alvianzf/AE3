import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const entries = await get(fetch, '/me/entries').catch(() => []);
	return { entries };
}
