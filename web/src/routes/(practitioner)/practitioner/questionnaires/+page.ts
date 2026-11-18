import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	// A Basic-plan practitioner hits require_pro_practitioner's 403 here —
	// same fallback-to-empty pattern as the Library weights page
	// (../knowledge/+page.ts), not a crash.
	const questionnaires = await get(fetch, '/me/questionnaires').catch(() => []);
	// Client Intake Links: a follow-up questionnaire's link is bound to a
	// specific client, picked here.
	const clients = await get(fetch, '/me/clients').catch(() => []);
	return { questionnaires, clients };
}
