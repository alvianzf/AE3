<script lang="ts">
	import PublicNav from '$lib/components/PublicNav.svelte';
	import PublicFooter from '$lib/components/PublicFooter.svelte';
	let { children } = $props();
</script>

<PublicNav />
<main>
	{@render children()}
</main>
<PublicFooter />

<style>
	main { min-height: 70dvh; }
</style>
