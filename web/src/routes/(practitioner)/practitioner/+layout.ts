import { redirect } from '@sveltejs/kit';
import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	// Real, measured latency issue (not a code-size one): each round trip to
	// the origin runs ~1-2s from a distant client, so two *sequential*
	// awaits here doubled every practitioner-portal navigation's critical
	// path. Both only need the already-attached session cookie, not each
	// other's result — running them together halves that.
	const [session, profile] = await Promise.all([
		get(fetch, '/auth/me').catch(() => null),
		get(fetch, '/me/profile').catch(() => null)
	]);
	if (!session || session.role !== 'practitioner') throw redirect(303, '/login');
	return { session, profile };
}
