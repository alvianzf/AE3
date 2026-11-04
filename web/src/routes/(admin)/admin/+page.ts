import { get } from '$lib/api';

export const ssr = false;

// Direct feedback: landing straight in the Library's dense tabs/sidebar/
// grid gave an admin no "what do I do next" moment — now the portal's
// root is this simple, action-first Dashboard; the Library itself moved
// to /admin/library, one deliberate click away via the one primary CTA
// below, not the first thing on screen.
export async function load({ fetch }) {
	const [stats, llmProvider] = await Promise.all([
		get(fetch, '/admin/stats').catch(() => ({})),
		get(fetch, '/superadmin/llm-provider').catch(() => null)
	]);
	return { stats, llmProvider: llmProvider?.provider ?? null };
}
