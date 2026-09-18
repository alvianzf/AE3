import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [sources, profile] = await Promise.all([
		get(fetch, '/me/knowledge').catch(() => []),
		get(fetch, '/me/profile').catch(() => null)
	]);
	// /api/staged 403s for a practitioner without can_upload_library, so
	// only fetch it once we know the grant is there.
	const staged = profile?.can_upload_library ? await get(fetch, '/staged').catch(() => []) : [];
	return { sources, canUploadLibrary: !!profile?.can_upload_library, staged };
}
