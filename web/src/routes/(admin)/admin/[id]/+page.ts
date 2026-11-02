import { get } from '$lib/api';

export const ssr = false;

export async function load({ fetch, params, url }) {
	const source = await get(fetch, `/sources/${params.id}/text`);
	return { source, locator: url.searchParams.get('locator') ?? '' };
}
