import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [sources, profile, personalStaged] = await Promise.all([
		get(fetch, '/me/knowledge').catch(() => []),
		get(fetch, '/me/profile').catch(() => null),
		// Any Pro practitioner can reach this one (specs/v6.10/01) —
		// unlike the shared staging routes below, it's not gated behind
		// can_upload_library.
		get(fetch, '/me/knowledge/stage').catch(() => [])
	]);
	// /api/staged (and /api/ingestion-jobs/active) 403 for a practitioner
	// without can_upload_library, so only fetch either once we know the
	// grant is there.
	const [staged, activeJobs] = profile?.can_upload_library
		? await Promise.all([
				get(fetch, '/staged').catch(() => []),
				// Resume any ingest still running server-side, same reasoning
				// as the admin Library page's +page.ts.
				get(fetch, '/ingestion-jobs/active').catch(() => [])
			])
		: [[], []];
	return {
		sources, canUploadLibrary: !!profile?.can_upload_library, staged, activeJobs,
		personalStaged, practitionerId: profile?.id ?? null
	};
}
