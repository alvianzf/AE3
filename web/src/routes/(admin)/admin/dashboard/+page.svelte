<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';

	let { data } = $props();
	const s = $derived(data.stats ?? {});
</script>

<svelte:head><title>Dashboard — Admin portal</title></svelte:head>

<h1>Site stats</h1>
<p class="hint">A quick read on the whole platform.</p>

<div class="grid-auto tiles">
	{#each Object.entries(s) as [key, value] (key)}
		<StatTile label={key.replaceAll('_', ' ')} value={String(value)} />
	{/each}
</div>

<style>
	.tiles { margin-top: var(--space-5); }
</style>
