import { PUBLIC_API_BASE, PUBLIC_API_BASE_BUILD, PUBLIC_SITE_URL } from '$env/static/public';

// Prerendered at build time, same as every other public route
// (svelte.config.js) — adapter-static has no server to answer this
// dynamically at runtime, so the sitemap is only as fresh as the last
// deploy, same staleness window the prerendered /practitioners listing
// already has (see that page's own comment on this tradeoff).
export const prerender = true;

const STATIC_PATHS = ['/', '/practitioners', '/join', '/login', '/signup'];

export async function GET() {
	let practitionerIds: string[] = [];
	try {
		const res = await fetch(`${PUBLIC_API_BASE_BUILD || PUBLIC_API_BASE}/api/practitioners`);
		const list = await res.json();
		practitionerIds = list.map((p: any) => p.id);
	} catch {
		// Build-time fetch failing shouldn't fail the whole build — same
		// fallback coach/[id]'s own entries() uses.
	}

	const urls = [
		...STATIC_PATHS,
		...practitionerIds.map((id) => `/coach/${id}`)
	];

	const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map((path) => `  <url><loc>${PUBLIC_SITE_URL}${path}</loc></url>`).join('\n')}
</urlset>
`;

	return new Response(body, { headers: { 'Content-Type': 'application/xml' } });
}
