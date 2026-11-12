<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	let {
		label,
		icon = 'more-vertical',
		items
	}: { label: string; icon?: string; items: Snippet } = $props();

	let open = $state(false);
	let wrapEl = $state<HTMLDivElement>();
	let triggerEl = $state<HTMLButtonElement>();
	let pos = $state({ top: 0, right: 0 });

	function toggle(e: MouseEvent) {
		e.stopPropagation();
		open = !open;
		if (open && triggerEl) {
			const r = triggerEl.getBoundingClientRect();
			pos = { top: r.bottom + 4, right: window.innerWidth - r.right };
		}
	}
	function close() {
		open = false;
	}

	$effect(() => {
		if (!open) return;
		function onDocClick(e: MouseEvent) {
			if (wrapEl && !wrapEl.contains(e.target as Node)) close();
		}
		function onKeydown(e: KeyboardEvent) {
			if (e.key === 'Escape') close();
		}
		function onScroll() {
			close();
		}
		document.addEventListener('click', onDocClick, true);
		document.addEventListener('keydown', onKeydown);
		document.addEventListener('scroll', onScroll, true);
		return () => {
			document.removeEventListener('click', onDocClick, true);
			document.removeEventListener('keydown', onKeydown);
			document.removeEventListener('scroll', onScroll, true);
		};
	});
</script>

<div class="menu-wrap" bind:this={wrapEl}>
	<button bind:this={triggerEl} class="menu-trigger" onclick={toggle} title={label} aria-label={label} aria-expanded={open}>
		<Icon name={icon} size={icon === 'more-vertical' ? 17 : 15} />
	</button>
	{#if open}
		<div class="menu-pop" style="top: {pos.top}px; right: {pos.right}px;" onclick={close}>
			{@render items()}
		</div>
	{/if}
</div>

<style>
	.menu-wrap { position: relative; display: inline-flex; }
	.menu-trigger {
		display: flex; align-items: center; justify-content: center;
		width: 2.1rem; height: 2.1rem; border: none; background: none; border-radius: var(--r);
		color: var(--ink-2); cursor: pointer; padding: 0;
		transition: background .12s var(--ease), color .12s var(--ease);
	}
	.menu-trigger:hover { background: var(--panel-2); color: var(--ink); }
	.menu-pop {
		position: fixed;
		padding: .35rem; border: 1px solid var(--line); border-radius: 12px;
		background: var(--panel);
		min-width: 12rem;
		display: flex; flex-direction: column; gap: 2px; z-index: 1000;
		animation: fadeIn .12s var(--ease) both;
	}
	.menu-pop :global(button), .menu-pop :global(a) {
		display: flex; align-items: center; gap: .6rem; width: 100%; text-align: left;
		border: none; background: none; cursor: pointer; font: inherit; font-size: var(--text-sm);
		font-weight: 500; color: var(--ink); padding: .5rem .75rem; border-radius: 8px; text-decoration: none;
		transition: background .12s var(--ease), color .12s var(--ease);
	}
	.menu-pop :global(button:hover), .menu-pop :global(a:hover) { background: var(--accent-soft); color: var(--accent-ink); }
	.menu-pop :global(button.danger) { color: var(--danger); }
	.menu-pop :global(button.danger:hover) { background: var(--danger-soft); color: var(--danger); }
	.menu-pop :global(button:disabled) { opacity: .45; cursor: not-allowed; }
	.menu-pop :global(button:disabled:hover) { background: none; color: var(--ink); }
</style>
