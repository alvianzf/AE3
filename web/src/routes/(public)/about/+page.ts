import { redirect } from '@sveltejs/kit';

// specs/v4.1/01 — /about's pitch content is now the landing page at "/";
// keeping this as a second page saying the same thing would just be a
// duplicate, and anyone with the old URL bookmarked/shared still lands
// somewhere real instead of a 404.
export const prerender = true;

export function load() {
	throw redirect(308, '/');
}
