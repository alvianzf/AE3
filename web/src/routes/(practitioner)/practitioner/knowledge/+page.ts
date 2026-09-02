import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const sources = await get(fetch, '/me/knowledge').catch(() => []);
	return { sources };
}
