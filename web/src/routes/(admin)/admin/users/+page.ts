import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [practitioners, admins, clients] = await Promise.all([
		get(fetch, '/admin/practitioners').catch(() => []),
		get(fetch, '/superadmin/admins').catch(() => []),
		get(fetch, '/admin/clients').catch(() => [])
	]);
	// /admin/clients already fans out across every pro practitioner's
	// vault and tags each row with practitioner_id, so the per-practitioner
	// count is just a groupby over data already being fetched — no need
	// for N separate /admin/practitioners/{id}/client-count round trips.
	const countByPractitioner = new Map<string, number>();
	for (const c of clients) {
		countByPractitioner.set(c.practitioner_id, (countByPractitioner.get(c.practitioner_id) ?? 0) + 1);
	}
	const withCounts = practitioners.map((p: any) => ({
		...p,
		clients: p.plan === 'pro' ? (countByPractitioner.get(p.id) ?? 0) : null
	}));
	return { practitioners: withCounts, admins, clients };
}
