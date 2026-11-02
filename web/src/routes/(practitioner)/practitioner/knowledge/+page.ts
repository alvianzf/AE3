import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	// GET /api/ingestion-jobs/active (app/main.py) is reachable by any Pro
	// practitioner — require_admin_or_pro_practitioner, not the
	// upload-permitted-only gate — specifically so a personal-knowledge-
	// base-only practitioner (specs/v6.10/01) can resume their own job's
	// progress after a reload too, same as GET /me/knowledge/stage below.
	const [sources, profile, personalStaged, activeJobs] = await Promise.all([
		get(fetch, '/me/knowledge').catch(() => []),
		get(fetch, '/me/profile').catch(() => null),
		get(fetch, '/me/knowledge/stage').catch(() => []),
		get(fetch, '/ingestion-jobs/active').catch(() => [])
	]);
	// /api/staged is still can_upload_library-only (the shared-library
	// staging surface), so only fetch it once we know that grant is there.
	const staged = profile?.can_upload_library
		? await get(fetch, '/staged').catch(() => [])
		: [];
	return {
		sources, canUploadLibrary: !!profile?.can_upload_library, staged, activeJobs,
		personalStaged, practitionerId: profile?.id ?? null
	};
}
