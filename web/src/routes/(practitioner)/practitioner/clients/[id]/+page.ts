import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch, params }) {
	const [client, sessions, documents, intake, files] = await Promise.all([
		get(fetch, `/me/clients/${params.id}`),
		get(fetch, `/me/clients/${params.id}/sessions`).catch(() => []),
		get(fetch, `/me/clients/${params.id}/documents`).catch(() => []),
		get(fetch, `/me/clients/${params.id}/intake`).catch(() => null),
		get(fetch, `/me/clients/${params.id}/files`).catch(() => [])
	]);
	return { client, sessions, documents, intake, files };
}
