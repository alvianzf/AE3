<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import Toaster from '$lib/components/Toaster.svelte';
	import NavProgress from '$lib/components/NavProgress.svelte';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<NavProgress />
{@render children()}
<Toaster />
