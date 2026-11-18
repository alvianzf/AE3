import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const clients = await get(fetch, '/me/clients').catch(() => []);
	// The document pane's letterhead needs the practitioner's own name/logo
	// — loaded here alongside the client list so DocumentPane never has to
	// fetch its own copy of the same profile.
	const profile = await get(fetch, '/me/profile').catch(() => null);
	return { clients, profile };
}
