import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const contacts = await get(fetch, '/me/contacts').catch(() => []);
	return { contacts };
}
