import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch, params }) {
	const [client, sessions, documents, intake, files, entries, links, questionnaires] = await Promise.all([
		get(fetch, `/me/clients/${params.id}`),
		get(fetch, `/me/clients/${params.id}/sessions`).catch(() => []),
		get(fetch, `/me/clients/${params.id}/documents`).catch(() => []),
		get(fetch, `/me/clients/${params.id}/intake`).catch(() => null),
		get(fetch, `/me/clients/${params.id}/files`).catch(() => []),
		get(fetch, `/me/clients/${params.id}/entries`).catch(() => []),
		get(fetch, `/me/clients/${params.id}/links`).catch(() => []),
		// For the "Send a questionnaire" action directly on this page —
		// journey redesign: sending a follow-up used to mean leaving the
		// client entirely, going to the separate Questionnaires page, and
		// re-finding this same client in a dropdown there.
		get(fetch, `/me/questionnaires`).catch(() => [])
	]);
	return { client, sessions, documents, intake, files, entries, links, questionnaires };
}
