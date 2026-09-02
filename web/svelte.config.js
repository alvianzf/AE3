import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		// Static adapter per specs/v4/01-sveltekit-frontend.md: FastAPI keeps
		// serving the build output, no new Node server process.
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'app.html',
			precompress: false,
			strict: false
		}),
		prerender: {
			// Dynamic coach/[id] entries are enumerated for real via entries()
			// (see src/routes/(public)/coach/[id]/+page.ts) against a live
			// backend at build time. Warn rather than fail on any edge the
			// crawler hits independently of that list — this is a content-
			// driven route, not a bug in the route tree.
			handleHttpError: 'warn',
			handleMissingId: 'warn',
			handleUnseenRoutes: 'warn'
		}
	}
};

export default config;
