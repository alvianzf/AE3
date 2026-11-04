<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	// Replaces Spotlight.svelte + Quiet.svelte entirely — no boxed "panel"
	// wrapping the whole page any more. A Workspace is the page itself:
	// a back-to-Home arrow, a big plain title, one optional primary
	// action, and the content below with room to breathe. Used by every
	// portal sub-page in place of the two old wrappers.
	let {
		title,
		backHref,
		backLabel = 'Home',
		actions,
		children
	}: {
		title: string;
		backHref?: string;
		backLabel?: string;
		actions?: Snippet;
		children: Snippet;
	} = $props();
</script>

<div class="workspace">
	<header class="ws-head">
		<div class="ws-title-row">
			{#if backHref}
				<a class="back" href={backHref} aria-label="Back to {backLabel}">
					<Icon name="chevron" size={16} />
				</a>
			{/if}
			<h1>{title}</h1>
		</div>
		{#if actions}<div class="ws-actions">{@render actions()}</div>{/if}
	</header>
	<div class="ws-body">
		{@render children()}
	</div>
</div>

<style>
	.workspace { display: flex; flex-direction: column; gap: var(--space-5); animation: fadeIn .25s var(--ease) both; }
	.ws-head {
		display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4);
		flex-wrap: wrap; padding-bottom: var(--space-4); border-bottom: 1px solid var(--line);
	}
	.ws-title-row { display: flex; align-items: center; gap: var(--space-3); min-width: 0; }
	.back {
		display: flex; align-items: center; justify-content: center; width: 2.2rem; height: 2.2rem;
		border-radius: 50%; background: var(--panel-2); color: var(--ink-2); text-decoration: none;
		transform: rotate(90deg); flex: 0 0 auto;
	}
	.back:hover { background: var(--accent-soft); color: var(--accent-ink); }
	h1 { font-size: var(--text-2xl); font-weight: var(--weight-bold); }
	.ws-actions { display: flex; gap: var(--space-2); flex: 0 0 auto; }
	.ws-body { min-width: 0; }
</style>
