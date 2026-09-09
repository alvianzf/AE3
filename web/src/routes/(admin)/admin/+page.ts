import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [sourcesRes, graph, audit, coverage, facets] = await Promise.all([
		get(fetch, '/sources?per_page=200').catch(() => ({ sources: [], total: 0 })),
		get(fetch, '/graph').catch(() => null),
		get(fetch, '/audit').catch(() => []),
		get(fetch, '/coverage').catch(() => []),
		get(fetch, '/facets').catch(() => ({ topics: [], kinds: [] }))
	]);
	return {
		sources: sourcesRes?.sources ?? sourcesRes ?? [],
		graph,
		audit,
		coverage,
		kinds: facets?.kinds ?? []
	};
}
