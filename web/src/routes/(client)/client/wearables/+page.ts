import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const connections = await get(fetch, '/me/wearables').catch(() => []);
	return { connections };
}
