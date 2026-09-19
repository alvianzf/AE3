import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [sourcesRes, graph, coverage, facets, staged, activeJobs] = await Promise.all([
		get(fetch, '/sources?per_page=200').catch(() => ({ sources: [], total: 0 })),
		get(fetch, '/graph').catch(() => null),
		get(fetch, '/coverage').catch(() => []),
		get(fetch, '/facets').catch(() => ({ topics: [], kinds: [] })),
		get(fetch, '/staged').catch(() => []),
		// Any ingest still running server-side (app/main.py's
		// GET /api/ingestion-jobs/active) — lets the page resume showing its
		// progress bar on load/reload instead of only while the tab that
		// started it stays open.
		get(fetch, '/ingestion-jobs/active').catch(() => [])
	]);
	return {
		sources: sourcesRes?.sources ?? sourcesRes ?? [],
		graph,
		coverage,
		kinds: facets?.kinds ?? [],
		staged,
		activeJobs
	};
}
