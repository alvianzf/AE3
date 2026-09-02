import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	// Local verification only: FastAPI has no CORS middleware (matches
	// production, which never needs it — same origin there). Proxying /api
	// here mimics that same-origin shape for `vite preview` against a
	// backend running on a different port. See src/lib/api.ts.
	server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
	preview: { proxy: { '/api': 'http://127.0.0.1:8000' } }
});
