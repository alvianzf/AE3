import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	// A Basic-plan practitioner hits require_pro_practitioner's 403 here —
	// same fallback-to-empty pattern as the Library weights page
	// (../knowledge/+page.ts), not a crash.
	const questionnaires = await get(fetch, '/me/questionnaires').catch(() => []);
	return { questionnaires };
}
