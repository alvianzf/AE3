<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		open = $bindable(false),
		title,
		children,
		footer
	}: { open?: boolean; title: string; children: Snippet; footer?: Snippet } = $props();

	let dialogEl: HTMLDialogElement;

	$effect(() => {
		if (!dialogEl) return;
		if (open && !dialogEl.open) dialogEl.showModal();
		if (!open && dialogEl.open) dialogEl.close();
	});

	function onClose() {
		open = false;
	}
</script>

<dialog bind:this={dialogEl} onclose={onClose} onclick={(e) => { if (e.target === dialogEl) dialogEl.close(); }}>
	<div class="dh">
		<h3>{title}</h3>
		<button class="x" onclick={() => dialogEl.close()} aria-label="Close">&times;</button>
	</div>
	<div class="db">{@render children()}</div>
	{#if footer}<div class="df">{@render footer()}</div>{/if}
</dialog>

<style>
	dialog {
		border: none; border-radius: var(--r-lg); padding: 0; width: min(32rem, 92vw);
		box-shadow: var(--shadow-lg); background: var(--panel);
		animation: liftIn .2s var(--ease) both;
	}
	dialog::backdrop { background: rgba(34, 31, 27, .45); backdrop-filter: blur(2px); }
	.dh { display: flex; align-items: center; justify-content: space-between; padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--line); }
	.dh h3 { font-size: var(--text-lg); }
	.x { border: none; background: none; font-size: 1.4rem; line-height: 1; cursor: pointer; color: var(--muted); }
	.db { padding: var(--space-4) var(--space-5); display: grid; gap: var(--space-3); }
	.df { padding: var(--space-3) var(--space-5) var(--space-4); display: flex; justify-content: flex-end; gap: var(--space-2); border-top: 1px solid var(--line); }
</style>
