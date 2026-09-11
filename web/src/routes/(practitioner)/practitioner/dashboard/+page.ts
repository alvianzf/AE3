import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	// specs/v4.1/03 CR2 — the onboarding checklist used to hardcode step 1
	// as done and check an unrelated counter for step 2; both now check the
	// thing they claim to check, which needs the client list loaded here.
	const [notifications, recentSessions, contacts, clients] = await Promise.all([
		get(fetch, '/me/notifications').catch(() => ({ new_contacts: 0, unviewed_intake: 0 })),
		get(fetch, '/me/sessions/recent').catch(() => []),
		get(fetch, '/me/contacts?status=new').catch(() => []),
		get(fetch, '/me/clients').catch(() => [])
	]);
	return { notifications, recentSessions, contacts, clients };
}
