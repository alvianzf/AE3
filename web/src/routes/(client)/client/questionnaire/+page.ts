import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [questionnaire, response] = await Promise.all([
		get(fetch, '/me/questionnaire').catch(() => null),
		get(fetch, '/me/questionnaire/response').catch(() => null)
	]);
	return { questionnaire, response };
}
