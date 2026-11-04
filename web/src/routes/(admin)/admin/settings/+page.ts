import { redirect } from '@sveltejs/kit';
import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch }) {
	const [llmProvider, health] = await Promise.all([
		get(fetch, '/superadmin/llm-provider').catch(() => null),
		get(fetch, '/health').catch(() => null)
	]);
	return { llmProvider: llmProvider?.provider ?? null, health };
}
