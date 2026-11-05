<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	// A tidy "⋮" dropdown for a card's action row (specs/v6.14). Explicit
	// $state-driven open/close, not the native `popover` attribute this
	// component first shipped with — found live, 2026-11-04: the popover
	// build either rendered open by default (an earlier CSS bug, fixed)
	// or, for at least one real user, didn't open on click at all —
	// almost certainly a Popover API support/behavior gap in that
	// browser, which a native-attribute approach has no fallback for.
	// This menu now gates core actions (Move, Delete, Private/public,
	// Edit access, Assign uploader) on every doc row across the whole
	// Library, so "guaranteed to work everywhere" beats "less code" —
	// explicit state + a window click/Escape listener works identically
	// in any browser this app already supports, no feature-detection
	// needed.
	let {
		label,
		icon = 'more-vertical',
		items
	}: { label: string; icon?: string; items: Snippet } = $props();

	let open = $state(false);
	let wrapEl = $state<HTMLDivElement>();
	let triggerEl = $state<HTMLButtonElement>();
	// Found live: inside a scrolling pane (e.g. the Library's .inspector
	// aside, overflow-y: auto), an absolutely-positioned popover is
	// clipped by that ancestor's overflow box — it rendered half-hidden.
	// Fixed positioning, computed from the trigger's own screen position,
	// escapes every ancestor's overflow/clip the same way a native
	// context menu would.
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
		// Capture phase, not bubble — a menu item's own onclick (e.g.
		// askDelete) should close the menu too, and listening on
		// 'click' in the bubble phase after the item's handler already
		// ran risks the item's own state change (a dialog opening, say)
		// racing this listener's close(). Capture fires before any of
		// that, so close() always runs first and consistently.
		function onDocClick(e: MouseEvent) {
			if (wrapEl && !wrapEl.contains(e.target as Node)) close();
		}
		function onKeydown(e: KeyboardEvent) {
			if (e.key === 'Escape') close();
		}
		// Fixed-position popover: a scroll anywhere (e.g. the Library's
		// scrolling .inspector aside) moves the trigger out from under it
		// unless we recompute — simplest is just to close, same as a
		// native context menu would on scroll.
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
		<!-- Not role="menu"/"menuitem" — that ARIA pattern expects roving-
		     tabindex arrow-key navigation between items, which this
		     doesn't implement; each item is already its own real,
		     individually-focusable <button>/<a>, which is accessible on
		     its own without that extra scaffolding half-built on top. -->
		<div class="menu-pop" style="top: {pos.top}px; right: {pos.right}px;" onclick={close}>
			{@render items()}
		</div>
	{/if}
</div>

<style>
	.menu-wrap { position: relative; display: inline-flex; }
	/* Own scoped class, not the generic "icon-btn" every page redefines
	   locally (border/background differ page to page) — found live:
	   the "⋮" trigger inherited whatever that page's own .icon-btn
	   happened to look like, so it was a different control (bordered
	   here, bare there) depending on where it sat. No border, no
	   background by default, anywhere this component is used. */
	.menu-trigger {
		display: flex; align-items: center; justify-content: center;
		width: 2rem; height: 2rem; border: none; background: none; border-radius: var(--r);
		color: var(--ink-2); cursor: pointer; padding: 0;
	}
	.menu-trigger:hover { background: var(--panel-2); color: var(--ink); }
	.menu-pop {
		position: fixed;
		padding: .3rem; border: 1px solid var(--glass-border); border-radius: var(--r-lg);
		background: var(--panel); background-image: var(--glass-sheen);
		backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur);
		box-shadow: var(--shadow-lg); min-width: 11rem;
		display: grid; gap: .1rem; z-index: 50;
	}
	/* Each item is whatever the caller renders (a <button> or <a>, danger
	   or not) — this just normalizes their shared layout so callers don't
	   repeat it at every call site. */
	.menu-pop :global(button), .menu-pop :global(a) {
		display: flex; align-items: center; gap: .5rem; width: 100%; text-align: left;
		border: none; background: none; cursor: pointer; font: inherit; font-size: var(--text-sm);
		color: var(--ink); padding: .5rem .6rem; border-radius: var(--r); text-decoration: none;
	}
	.menu-pop :global(button:hover), .menu-pop :global(a:hover) { background: var(--panel-2); }
	.menu-pop :global(button.danger) { color: var(--danger); }
	.menu-pop :global(button.danger:hover) { background: color-mix(in srgb, var(--danger) 10%, transparent); }
	.menu-pop :global(button:disabled) { opacity: .5; cursor: not-allowed; }
	.menu-pop :global(button:disabled:hover) { background: none; }
</style>
