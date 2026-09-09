import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const audit = await get(fetch, '/audit').catch(() => []);
	return { audit };
}
