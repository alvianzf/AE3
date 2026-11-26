import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch, params }) {
	const [client, sessions, documents, intake, record, links, questionnaires] = await Promise.all([
		get(fetch, `/me/clients/${params.id}`),
		get(fetch, `/me/clients/${params.id}/sessions`).catch(() => []),
		get(fetch, `/me/clients/${params.id}/documents`).catch(() => []),
		get(fetch, `/me/clients/${params.id}/intake`).catch(() => null),
		// The unified Record tab's one data source — entries (manual and
		// upload-backed, each carrying AI doc_type/summary/highlights when
		// it has a file) plus current lab-marker trends, already joined
		// server-side (app/vault.py's get_client_record). Replaces the old
		// separate /entries + /files fetches this page used to merge itself.
		get(fetch, `/me/clients/${params.id}/record`).catch(() => ({ entries: [], clinical_state: [] })),
		get(fetch, `/me/clients/${params.id}/links`).catch(() => []),
		// For the "Send a questionnaire" action directly on this page —
		// journey redesign: sending a follow-up used to mean leaving the
		// client entirely, going to the separate Questionnaires page, and
		// re-finding this same client in a dropdown there.
		get(fetch, `/me/questionnaires`).catch(() => [])
	]);
	return { client, sessions, documents, intake, record, links, questionnaires };
}
