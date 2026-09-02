import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [sourcesRes, graph, audit] = await Promise.all([
		get(fetch, '/sources').catch(() => ({ sources: [], total: 0 })),
		get(fetch, '/graph').catch(() => null),
		get(fetch, '/audit').catch(() => [])
	]);
	return { sources: sourcesRes?.sources ?? sourcesRes ?? [], graph, audit };
}
