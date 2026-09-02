import { redirect } from '@sveltejs/kit';
import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const session = await get(fetch, '/auth/me').catch(() => null);
	if (!session || session.role !== 'client') throw redirect(303, '/login');
	return { session };
}
