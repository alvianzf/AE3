<script lang="ts">
	import type { Snippet } from 'svelte';
	// A plain sub-section inside a Workspace — for pages with several
	// panels on one screen (a client's record: overview/files/sessions),
	// where repeating Workspace's own back-arrow+title per panel would be
	// wrong. Just a label and content, no card chrome around it.
	let { title, children }: { title: string; children: Snippet } = $props();
</script>

<section class="section">
	<h2>{title}</h2>
	{@render children()}
</section>

<style>
	.section { margin-bottom: var(--space-6); }
	.section h2 { font-size: var(--text-lg); font-weight: var(--weight-bold); margin-bottom: var(--space-3); }
</style>
