import { error } from '@sveltejs/kit';

// Only reachable from /join's own form submit, which is itself hidden now
// (see ../+page.ts) — hidden the same way for consistency.
export const prerender = true;

export function load() {
	error(404, 'Not found');
}
