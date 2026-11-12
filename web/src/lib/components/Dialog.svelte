<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		open = $bindable(false),
		title,
		wide = false,
		children,
		footer
	}: { open?: boolean; title: string; wide?: boolean; children: Snippet; footer?: Snippet } = $props();

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

<dialog bind:this={dialogEl} class:wide onclose={onClose} onclick={(e) => { if (e.target === dialogEl) dialogEl.close(); }}>
	<div class="dh">
		<h3>{title}</h3>
		<button class="x" onclick={() => dialogEl.close()} aria-label="Close">&times;</button>
	</div>
	<div class="db">{@render children()}</div>
	{#if footer}<div class="df">{@render footer()}</div>{/if}
</dialog>

<style>
	dialog {
		border: 1px solid var(--line); border-radius: 16px; padding: 0; width: min(32rem, 92vw);
		max-height: min(90dvh, 90vh);
		background: var(--panel);
		color: var(--ink);
		animation: liftIn .18s var(--ease) both;
	}
	dialog[open] {
		display: flex;
		flex-direction: column;
	}
	dialog.wide { width: min(48rem, 94vw); }
	dialog::backdrop { background: rgba(15, 23, 42, .55); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); }
	.dh {
		display: flex; align-items: center; justify-content: space-between; flex: 0 0 auto;
		padding: var(--space-4) var(--space-5); border-bottom: 1px solid var(--line);
	}
	.dh h3 { font-size: 1.15rem; font-weight: 700; color: var(--ink); letter-spacing: -.01em; margin: 0; }
	.x {
		display: inline-flex; align-items: center; justify-content: center; width: 2rem; height: 2rem;
		border: none; background: none; font-size: 1.25rem; line-height: 1; cursor: pointer; color: var(--muted);
		border-radius: 8px; transition: background .12s var(--ease), color .12s var(--ease);
	}
	.x:hover { background: var(--panel-2); color: var(--ink); }
	.db {
		padding: var(--space-5); display: grid; gap: var(--space-4);
		flex: 1 1 auto; overflow-y: auto; overscroll-behavior: contain;
	}
	.df {
		padding: var(--space-4) var(--space-5); display: flex; justify-content: flex-end; gap: var(--space-2); flex: 0 0 auto;
		border-top: 1px solid var(--line); background: var(--panel-2); border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;
	}
</style>
