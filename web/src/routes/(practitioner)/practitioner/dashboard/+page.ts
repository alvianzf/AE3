import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [notifications, recentSessions, contacts] = await Promise.all([
		get(fetch, '/me/notifications').catch(() => ({ new_contacts: 0, unviewed_intake: 0 })),
		get(fetch, '/me/sessions/recent').catch(() => []),
		get(fetch, '/me/contacts?status=new').catch(() => [])
	]);
	return { notifications, recentSessions, contacts };
}
