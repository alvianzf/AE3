<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	// A tidy "⋮" dropdown for a card's action row (specs/v6.14) — built on
	// the native `popover` attribute rather than a hand-rolled click-
	// outside/Escape/z-index listener set: the browser already gives a
	// popover light-dismiss (outside click or Escape closes it) and top-
	// layer stacking for free, the same reason Dialog.svelte already
	// leans on the native <dialog> element instead of reimplementing a
	// modal. Positioned with a plain CSS override (position: absolute
	// relative to the wrapper) rather than full CSS anchor positioning —
	// browser support for anchor positioning isn't there yet; a simple
	// "below and right-aligned to the trigger" placement is enough for
	// a card-corner menu that never needs to flip sides.
	let {
		label,
		items
	}: { label: string; items: Snippet } = $props();

	const id = `menu-${Math.random().toString(36).slice(2)}`;
</script>

<div class="menu-wrap">
	<button class="icon-btn" popovertarget={id} title={label} aria-label={label}>
		<Icon name="more-vertical" />
	</button>
	<div {id} popover class="menu-pop" role="menu">
		{@render items()}
	</div>
</div>

<style>
	.menu-wrap { position: relative; display: inline-flex; }
	.menu-pop {
		position: absolute; top: 100%; right: 0; left: auto; bottom: auto; margin: .25rem 0 0;
		padding: .3rem; border: 1px solid var(--line); border-radius: var(--r-lg);
		background: var(--panel); box-shadow: var(--shadow-lg); min-width: 11rem;
		gap: .1rem;
	}
	/* display must stay OUT of the base rule above — found live: an
	   unconditional `display: grid` there is author-origin CSS, which
	   always beats the UA stylesheet's default `[popover]:not(:popover-
	   open) { display: none }` regardless of selector specificity (author
	   styles win over user-agent styles in the cascade), so the menu
	   rendered open on every page load instead of only once triggered. */
	.menu-pop:popover-open { display: grid; }
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
