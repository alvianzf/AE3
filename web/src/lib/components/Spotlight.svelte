<script lang="ts">
	import type { Snippet } from 'svelte';
	// Public-site-only now (auth pages: login/signup/join/account) — the
	// three authenticated portals use the list/detail-pane shell instead.
	// Flat, bordered, no shadow — matches the rest of the rebuilt system.
	let {
		title,
		leaf = false,
		actions,
		children
	}: { title?: string; leaf?: boolean; actions?: Snippet; children: Snippet } = $props();
</script>

<section class="box" class:leafmark={leaf}>
	{#if title}
		<div class="head">
			<h2>{title}</h2>
			{#if actions}<div class="actions">{@render actions()}</div>{/if}
		</div>
	{/if}
	<div class="body">{@render children()}</div>
</section>

<style>
	.box { background: var(--panel); border: 1px solid var(--line); }
	.head {
		display: flex; align-items: center; justify-content: space-between; gap: var(--space-3);
		padding: var(--space-5) var(--space-6) var(--space-4); border-bottom: 1px solid var(--line);
	}
	.head h2 { font-size: var(--text-xl); font-weight: var(--weight-bold); }
	.body { padding: var(--space-5) var(--space-6); }
	.actions { display: flex; gap: .5rem; }
</style>
