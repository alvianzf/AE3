import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [practitioners, admins] = await Promise.all([
		get(fetch, '/admin/practitioners').catch(() => []),
		get(fetch, '/superadmin/admins').catch(() => [])
	]);
	return { practitioners, admins };
}
