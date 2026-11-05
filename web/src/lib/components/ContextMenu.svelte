<script lang="ts">
	import type { Snippet } from 'svelte';

	// A real OS-style right-click menu — floats from the cursor position,
	// not anchored to whatever element was clicked, and dismisses on any
	// outside click, a second right-click, Escape, or a scroll (same
	// reasoning as Menu.svelte's own fixed-position popover: nothing here
	// should stay pinned to a stale screen position).
	let {
		x, y, onClose, items
	}: { x: number; y: number; onClose: () => void; items: Snippet } = $props();

	let el: HTMLDivElement;

	$effect(() => {
		function onDocClick(e: MouseEvent) {
			if (el && !el.contains(e.target as Node)) onClose();
		}
		function onKeydown(e: KeyboardEvent) {
			if (e.key === 'Escape') onClose();
		}
		document.addEventListener('click', onDocClick, true);
		document.addEventListener('contextmenu', onDocClick, true);
		document.addEventListener('keydown', onKeydown);
		document.addEventListener('scroll', onClose, true);
		return () => {
			document.removeEventListener('click', onDocClick, true);
			document.removeEventListener('contextmenu', onDocClick, true);
			document.removeEventListener('keydown', onKeydown);
			document.removeEventListener('scroll', onClose, true);
		};
	});
</script>

<div class="ctx-menu" bind:this={el} style="top: {y}px; left: {x}px;" onclick={onClose}>
	{@render items()}
</div>

<style>
	.ctx-menu {
		position: fixed;
		padding: .35rem; border: 1px solid var(--line); border-radius: 12px;
		background: var(--panel);
		box-shadow: 0 10px 30px rgba(0, 0, 0, .14), 0 2px 6px rgba(0, 0, 0, .08);
		min-width: 13rem;
		display: flex; flex-direction: column; gap: 2px; z-index: 1000;
		animation: fadeIn .12s var(--ease) both;
	}
	.ctx-menu :global(button), .ctx-menu :global(a) {
		display: flex; align-items: center; gap: .6rem; width: 100%; text-align: left;
		border: none; background: none; cursor: pointer; font: inherit; font-size: var(--text-sm);
		font-weight: 500; color: var(--ink); padding: .5rem .75rem; border-radius: 8px; text-decoration: none;
		transition: background .12s var(--ease), color .12s var(--ease);
	}
	.ctx-menu :global(button:hover), .ctx-menu :global(a:hover) {
		background: var(--accent-soft);
		color: var(--accent-ink);
	}
	.ctx-menu :global(button.danger) { color: var(--danger); }
	.ctx-menu :global(button.danger:hover) {
		background: var(--danger-soft);
		color: var(--danger);
	}
	.ctx-menu :global(button:disabled) { opacity: .45; cursor: not-allowed; }
	.ctx-menu :global(button:disabled:hover) { background: none; color: var(--ink); }
</style>
