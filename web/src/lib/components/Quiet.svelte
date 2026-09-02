<script lang="ts">
	import type { Snippet } from 'svelte';
	// Tier 2: supporting content, quiet chrome, no red header.
	let { title, tight = false, children }: { title?: string; tight?: boolean; children: Snippet } = $props();
</script>

<section class="panel">
	{#if title}<div class="ph"><h3>{title}</h3></div>{/if}
	<div class="pb" class:tight>{@render children()}</div>
</section>
