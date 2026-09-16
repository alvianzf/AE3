<script lang="ts">
	import { PUBLIC_SITE_URL } from '$env/static/public';

	// Shared <head> tags for every public (indexable) page: title, meta
	// description, canonical, Open Graph + Twitter card, so each page only
	// has to supply its own title/description/path instead of repeating
	// the same dozen tags. `noindex` is for real pages that exist but
	// shouldn't be indexed (login, account, signup, join/submitted) —
	// still crawlable/linkable, just excluded from search results.
	let {
		title,
		description,
		path,
		image = '/og-image.png',
		type = 'website',
		noindex = false
	}: {
		title: string;
		description: string;
		path: string;
		image?: string;
		type?: 'website' | 'profile';
		noindex?: boolean;
	} = $props();

	const url = $derived(`${PUBLIC_SITE_URL}${path}`);
	const imageUrl = $derived(image.startsWith('http') ? image : `${PUBLIC_SITE_URL}${image}`);
</script>

<svelte:head>
	<title>{title}</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={url} />
	{#if noindex}
		<meta name="robots" content="noindex, follow" />
	{/if}

	<meta property="og:type" content={type} />
	<meta property="og:site_name" content="Clinic" />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={url} />
	<meta property="og:image" content={imageUrl} />

	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={title} />
	<meta name="twitter:description" content={description} />
	<meta name="twitter:image" content={imageUrl} />
</svelte:head>
