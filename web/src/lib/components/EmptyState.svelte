<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	// specs/v7/01 — a real empty-state component, replacing the bare
	// `<p class="hint">Nothing here yet.</p>` pattern repeated (with
	// slightly different wording each time) across the admin Library,
	// staged list, and elsewhere. The first thing a brand-new admin/
	// practitioner/client sees on most pages, before any data exists —
	// worth icon + headline + supporting copy + an optional primary
	// action, not a plain sentence that reads as a bug rather than a
	// deliberate "start here" moment.
	let {
		icon = 'book',
		title,
		body,
		action
	}: {
		icon?: string;
		title: string;
		body?: string;
		action?: Snippet;
	} = $props();
</script>

<div class="empty-state">
	<span class="empty-icon"><Icon name={icon} size={28} /></span>
	<h3>{title}</h3>
	{#if body}<p class="empty-body">{body}</p>{/if}
	{#if action}<div class="empty-action">{@render action()}</div>{/if}
</div>

<style>
	.empty-state {
		display: flex; flex-direction: column; align-items: center; text-align: center; gap: .5rem;
		padding: var(--space-6) var(--space-4); color: var(--muted);
		animation: fadeIn var(--duration-slow) var(--ease) both;
	}
	.empty-icon {
		display: inline-flex; align-items: center; justify-content: center;
		width: 3.25rem; height: 3.25rem; border-radius: 50%;
		background: var(--empty-ico-bg, var(--panel-2)); border: 1px solid var(--empty-ico-border, var(--line)); color: var(--empty-ico-ink, var(--muted));
	}
	.empty-state h3 { font-size: var(--text-base); color: var(--ink-2); font-weight: var(--weight-medium); }
	.empty-body { max-width: 26rem; font-size: var(--text-sm); }
	.empty-action { margin-top: var(--space-2); }
</style>
