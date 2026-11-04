import { get } from '$lib/api';

export const ssr = false;

// The practitioner portal's Home launcher — replaces the old Dashboard
// page as the root. Recent-history lists moved to where they actually
// belong (Consult's own sidebar, the Contacts page) instead of being
// duplicated here. notifications already comes from the parent
// layout's own load — not re-fetched here.
export async function load({ fetch }) {
	const [recentSessions, clients] = await Promise.all([
		get(fetch, '/me/sessions/recent').catch(() => []),
		get(fetch, '/me/clients').catch(() => [])
	]);
	return { recentSessions, clients };
}
