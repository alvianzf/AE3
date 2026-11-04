<script lang="ts">
	import type { Snippet } from 'svelte';
	// Public-site-only now (the coach/[id] profile page) — quieter than
	// Spotlight (no bottom border under the title), same flat system.
	let { title, tight = false, children }: { title?: string; tight?: boolean; children: Snippet } = $props();
</script>

<section class="box">
	{#if title}<div class="head"><h3>{title}</h3></div>{/if}
	<div class="body" class:tight>{@render children()}</div>
</section>

<style>
	.box { background: var(--panel); border: 1px solid var(--line); }
	.head { padding: var(--space-3) var(--space-4) 0; }
	.head h3 { font-size: var(--text-base); font-weight: var(--weight-bold); color: var(--ink-2); }
	.body { padding: var(--space-4); }
	.body.tight { padding: var(--space-3); }
</style>
