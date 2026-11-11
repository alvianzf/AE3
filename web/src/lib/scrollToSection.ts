import { browser } from '$app/environment';
import { goto } from '$app/navigation';

const PENDING_KEY = 'fhc-scroll-to';

// Nav/footer section links used to be plain `href="#id"` anchors, but
// PublicNav/PublicFooter are shared across every public route, not just
// the one-page homepage — on /practitioners, /signup, /coach/[id] etc.
// those ids don't exist, so the hash just did nothing (and SvelteKit's
// prerenderer warned on every one of them). This scrolls in place when
// already on `/`, and otherwise navigates home first and finishes the
// scroll once the homepage has mounted — no `#fragment` ever lands in
// the address bar either way.
export function goToSection(id: string, currentPath: string) {
	if (currentPath === '/') {
		document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
		return;
	}
	if (browser) sessionStorage.setItem(PENDING_KEY, id);
	goto('/');
}

// Call from the homepage's onMount to finish a cross-page scroll request.
export function consumePendingScroll() {
	if (!browser) return;
	const id = sessionStorage.getItem(PENDING_KEY);
	if (!id) return;
	sessionStorage.removeItem(PENDING_KEY);
	document.getElementById(id)?.scrollIntoView();
}
