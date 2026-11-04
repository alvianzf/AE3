// specs/v7/06 — a scroll-triggered reveal, extending the existing
// liftIn/fadeIn keyframes (app.css) from "once, on mount" to "as each
// section actually enters the viewport." Native IntersectionObserver,
// no new dependency. Adds a `.revealed` class the first time the
// element crosses the threshold, then stops observing — a one-way
// reveal, not a replay-on-every-scroll toggle, matching how liftIn/
// fadeIn already only ever play once per element.
export function reveal(node: HTMLElement, options: { threshold?: number } = {}) {
	// prefers-reduced-motion: app.css's existing global override already
	// collapses animation-duration to ~0 for anything marked `.revealed`
	// below, but an element that's *never* observed to intersect (e.g.
	// reduced-motion users who don't scroll far enough, or a very short
	// viewport) would otherwise stay invisible forever — so skip the
	// observer entirely and reveal immediately when the user has that
	// preference set, rather than relying on the animation override alone.
	if (typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches) {
		node.classList.add('revealed');
		return {};
	}

	const observer = new IntersectionObserver(
		([entry]) => {
			if (entry.isIntersecting) {
				node.classList.add('revealed');
				observer.disconnect();
			}
		},
		{ threshold: options.threshold ?? 0.15 }
	);
	observer.observe(node);

	return {
		destroy() {
			observer.disconnect();
		}
	};
}
