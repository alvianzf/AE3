<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import Toaster from '$lib/components/Toaster.svelte';
	import NavProgress from '$lib/components/NavProgress.svelte';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<!-- Brand type everywhere, not just the public site: the three portals
	     now share the FHC theme (see .portal rules in app.css), so they
	     need Bricolage Grotesque + Figtree too, not just (public)'s pages. -->
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link
		rel="stylesheet"
		href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700&family=Figtree:wght@400;500;600&display=swap"
	/>
</svelte:head>

<NavProgress />
{@render children()}
<Toaster />
