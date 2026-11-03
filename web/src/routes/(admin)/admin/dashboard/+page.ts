import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	// /superadmin/llm-provider 403s for a plain admin — harmless, same
	// catch-and-fall-back-to-undefined pattern. The page only renders the
	// toggle for a superadmin anyway (data.session.admin_role, from the
	// parent (admin)/+layout.ts load) — which now also loads /health for
	// the footer status bar, so this page doesn't need its own copy.
	const [stats, llmProvider] = await Promise.all([
		get(fetch, '/admin/stats').catch(() => ({})),
		get(fetch, '/superadmin/llm-provider').catch(() => null)
	]);
	return { stats, llmProvider: llmProvider?.provider ?? null };
}
