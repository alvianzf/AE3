import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const files = await get(fetch, '/me/files').catch(() => []);
	return { files };
}
