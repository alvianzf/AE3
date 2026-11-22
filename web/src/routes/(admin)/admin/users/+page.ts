import { redirect } from '@sveltejs/kit';
import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch, url }) {
	// The "Clients" tab moved to its own /admin/clients page
	// (ux-implementation-spec.md#4) — keep old ?tab=clients links working
	// for one release rather than silently dropping them.
	if (url.searchParams.get('tab') === 'clients') {
		const q = url.searchParams.get('q');
		throw redirect(302, `/admin/clients${q ? `?q=${encodeURIComponent(q)}` : ''}`);
	}
	const [practitioners, admins, clients] = await Promise.all([
		get(fetch, '/admin/practitioners').catch(() => []),
		get(fetch, '/superadmin/admins').catch(() => []),
		get(fetch, '/admin/clients').catch(() => [])
	]);
	// /admin/clients already fans out across every pro practitioner's
	// vault and tags each row with practitioner_id, so the per-practitioner
	// count is just a groupby over data already being fetched — no need
	// for N separate /admin/practitioners/{id}/client-count round trips.
	// Still fetched here (not just on the new Clients page) purely for
	// this per-practitioner count, not for display on this page.
	const countByPractitioner = new Map<string, number>();
	for (const c of clients) {
		countByPractitioner.set(c.practitioner_id, (countByPractitioner.get(c.practitioner_id) ?? 0) + 1);
	}
	const withCounts = practitioners.map((p: any) => ({
		...p,
		clients: p.plan === 'pro' ? (countByPractitioner.get(p.id) ?? 0) : null
	}));
	return { practitioners: withCounts, admins };
}
