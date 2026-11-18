import { get } from '$lib/api';

// No login, no session — a token-gated page that works for a client who
// has never created an account. ssr off for the same reason every other
// dynamic, per-visitor page in this app is (consult, client questionnaire):
// this is never meaningfully prerenderable.
export const ssr = false;

export async function load({ params, fetch }) {
	try {
		const data = await get(fetch, `/intake/${params.token}`);
		return { ...data, token: params.token, state: 'active' as const };
	} catch (err: any) {
		// 410 (already submitted) is distinct from every other failure —
		// the page shows a plain confirmation, not an error.
		if (err.status === 410) return { token: params.token, state: 'submitted' as const };
		return { token: params.token, state: 'invalid' as const };
	}
}
