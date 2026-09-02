import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const questionnaires = await get(fetch, '/admin/questionnaires').catch(() => []);
	return { questionnaires };
}
