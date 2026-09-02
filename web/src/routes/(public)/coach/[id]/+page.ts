import { error } from '@sveltejs/kit';
import { get } from '$lib/api';
import { PUBLIC_API_BASE, PUBLIC_API_BASE_BUILD } from '$env/static/public';

export const prerender = true;

// Enumerate every approved practitioner at build time so adapter-static can
// prerender each coach profile page (specs/v4/01 — public portal prerendered
// at build time; needs a real backend reachable during `npm run build`).
// entries() always runs in Node during the build, so it always wants the
// direct backend URL, never the browser-facing relative one.
export async function entries() {
	try {
		const res = await fetch(`${PUBLIC_API_BASE_BUILD || PUBLIC_API_BASE}/api/practitioners`);
		const list = await res.json();
		return list.map((p: any) => ({ id: p.id }));
	} catch {
		return [];
	}
}

export async function load({ params, fetch }) {
	const practitioner = await get(fetch, `/practitioners/${params.id}`).catch(() => null);
	if (!practitioner) throw error(404, 'No such practitioner');
	return { practitioner };
}
