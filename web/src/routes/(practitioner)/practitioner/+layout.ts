import { redirect } from '@sveltejs/kit';
import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	// Real, measured latency issue (not a code-size one): each round trip to
	// the origin runs ~1-2s from a distant client, so two *sequential*
	// awaits here doubled every practitioner-portal navigation's critical
	// path. Both only need the already-attached session cookie, not each
	// other's result — running them together halves that.
	const [session, profile, notifications] = await Promise.all([
		get(fetch, '/auth/me').catch(() => null),
		get(fetch, '/me/profile').catch(() => null),
		get(fetch, '/me/notifications').catch(() => ({ new_contacts: 0, unviewed_intake: 0 }))
	]);
	// An admin account acts as a practitioner directly under its own
	// identity (app/auth.py's require_practitioner/require_pro_practitioner
	// — no separate linked practitioner account, no Pro/approval gate),
	// so this layout has to accept that session shape too, not just a
	// literal practitioner login.
	if (!session || (session.role !== 'practitioner' && session.role !== 'admin')) throw redirect(303, '/login');
	return { session, profile, notifications };
}
