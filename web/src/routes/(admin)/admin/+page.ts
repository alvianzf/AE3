import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [sourcesRes, graph, coverage, facets, staged] = await Promise.all([
		get(fetch, '/sources?per_page=200').catch(() => ({ sources: [], total: 0 })),
		get(fetch, '/graph').catch(() => null),
		get(fetch, '/coverage').catch(() => []),
		get(fetch, '/facets').catch(() => ({ topics: [], kinds: [] })),
		get(fetch, '/staged').catch(() => [])
	]);
	return {
		sources: sourcesRes?.sources ?? sourcesRes ?? [],
		graph,
		coverage,
		kinds: facets?.kinds ?? [],
		staged
	};
}
