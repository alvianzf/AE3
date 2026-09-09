import { get } from '$lib/api';

export const ssr = false;

// Previously the dashboard had no loader at all -- every tile showed the
// same "not done yet" copy regardless of real status
// (specs/v4/04-known-issues.md#m14).
export async function load({ fetch }) {
	const [response, files, connections] = await Promise.all([
		get(fetch, '/me/questionnaire/response').catch(() => null),
		get(fetch, '/me/files').catch(() => []),
		get(fetch, '/me/wearables').catch(() => [])
	]);
	return { response, files, connections };
}
