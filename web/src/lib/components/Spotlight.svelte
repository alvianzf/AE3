<script lang="ts">
	import type { Snippet } from 'svelte';
	// Tier 1: the one panel per screen that's the reason someone opened it.
	let {
		title,
		leaf = false,
		actions,
		children
	}: { title?: string; leaf?: boolean; actions?: Snippet; children: Snippet } = $props();
</script>

<section class="card-panel" class:leafmark={leaf}>
	{#if title}
		<div class="ph botanic">
			<h2>{title}</h2>
			{#if actions}<div class="actions">{@render actions()}</div>{/if}
		</div>
	{/if}
	<div class="pb">{@render children()}</div>
</section>

<style>
	.actions { display: flex; gap: .5rem; }
</style>
