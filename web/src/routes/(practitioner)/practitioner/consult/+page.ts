import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const clients = await get(fetch, '/me/clients').catch(() => []);
	return { clients };
}
