<script lang="ts">
	import PublicNav from '$lib/components/PublicNav.svelte';
	let { children } = $props();
</script>

<PublicNav />
<main>
	{@render children()}
</main>

<style>
	main { min-height: 70dvh; }
</style>
