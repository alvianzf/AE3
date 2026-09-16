import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [audit, adminLog] = await Promise.all([
		get(fetch, '/audit').catch(() => []),
		get(fetch, '/superadmin/audit-log?per_page=50').catch(() => null)
	]);
	return { audit, adminLog };
}
