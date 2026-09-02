import { get } from '$lib/api';

export const prerender = true;

export async function load({ fetch }) {
	const practitioners = await get(fetch, '/practitioners').catch(() => []);
	return { practitioners };
}
