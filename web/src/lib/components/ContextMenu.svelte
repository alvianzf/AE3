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
		padding: .3rem; border: 1px solid var(--glass-border); border-radius: var(--r-lg);
		background: var(--panel); background-image: var(--glass-sheen);
		backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur);
		/* Floats free over arbitrary content (not anchored next to a
		   toolbar button like Menu.svelte's popover), so it needs a
		   stronger, more defined shadow to read as "above" the page
		   rather than blending into it. */
		box-shadow: var(--shadow-lg), 0 2px 8px rgba(20, 18, 16, .22);
		min-width: 11rem;
		display: grid; gap: .1rem; z-index: 50;
	}
	.ctx-menu :global(button), .ctx-menu :global(a) {
		display: flex; align-items: center; gap: .5rem; width: 100%; text-align: left;
		border: none; background: none; cursor: pointer; font: inherit; font-size: var(--text-sm);
		color: var(--ink); padding: .5rem .6rem; border-radius: var(--r); text-decoration: none;
	}
	.ctx-menu :global(button:hover), .ctx-menu :global(a:hover) { background: var(--panel-2); }
	.ctx-menu :global(button.danger) { color: var(--danger); }
	.ctx-menu :global(button.danger:hover) { background: color-mix(in srgb, var(--danger) 10%, transparent); }
	.ctx-menu :global(button:disabled) { opacity: .5; cursor: not-allowed; }
</style>
