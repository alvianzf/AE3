/** Marks <html> as a private (dashboard) surface so `surface.css` tokens apply.
 *  Call from a portal layout; the attributes are removed on destroy. */
export function useAppSurface(portal: 'admin' | 'practitioner' | 'client') {
	$effect(() => {
		const el = document.documentElement;
		el.dataset.surface = 'app';
		el.dataset.portal = portal;
		return () => {
			delete el.dataset.surface;
			delete el.dataset.portal;
		};
	});
}
