import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	// /superadmin/llm-provider 403s for a plain admin — harmless, same
	// catch-and-fall-back-to-undefined the other two calls already use,
	// and the page only renders the toggle for a superadmin anyway
	// (data.session.admin_role, from the parent (admin)/+layout.ts load).
	const [stats, health, llmProvider] = await Promise.all([
		get(fetch, '/admin/stats').catch(() => ({})),
		get(fetch, '/health').catch(() => null),
		get(fetch, '/superadmin/llm-provider').catch(() => null)
	]);
	return { stats, health, llmProvider: llmProvider?.provider ?? null };
}
