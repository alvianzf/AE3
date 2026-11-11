import { error } from '@sveltejs/kit';

// Hidden, not deleted: the practitioner-application flow is orphaned by
// the FHC single-practice pivot (no link points here any more), but the
// route stays on disk in case it's needed again. Renders the shared
// (public) 404 page instead of the old apply form.
export const prerender = true;

export function load() {
	error(404, 'Not found');
}
