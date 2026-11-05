<script lang="ts">
	import Icon from './Icon.svelte';

	let {
		label,
		value,
		href,
		icon,
		tone
	}: { label: string; value: string | number; href?: string; icon?: string; tone?: 'warn' } = $props();

	const Tag = $derived(href ? 'a' : 'div');
</script>

<svelte:element this={Tag} href={href} class="tile" class:warn={tone === 'warn'}>
	{#if icon}<span class="ico"><Icon name={icon} size={20} /></span>{/if}
	<div>
		<div class="val">{value}</div>
		<div class="lbl">{label}</div>
	</div>
</svelte:element>

<style>
	.tile {
		display: flex; align-items: center; gap: var(--space-3); padding: var(--space-4);
		background: var(--panel-2); border: 1px solid var(--line); border-radius: var(--tile-r, var(--r-lg)); box-shadow: var(--shadow-tile, none);
		text-decoration: none; color: inherit; animation: fadeIn .4s var(--ease) both;
		transition: border-color .15s var(--ease), transform .15s var(--ease);
	}
	a.tile:hover { border-color: var(--accent); transform: var(--tile-hover, translateY(-2px)); }
	.ico { display: inline-flex; align-items: center; justify-content: center; color: var(--accent-ink); flex: 0 0 auto; }
	.val { font-size: var(--tile-val, var(--text-xl)); font-weight: 700; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
	.lbl { font-size: var(--text-xs); color: var(--muted); letter-spacing: .04em; }
	.tile.warn { border-color: var(--warn); background: var(--warn-soft); }
	.tile.warn .ico, .tile.warn .val { color: var(--warn); }
	/* Portal hook: icon sits in a tinted rounded well. */
	.ico { width: var(--tile-ico, auto); height: var(--tile-ico, auto); border-radius: var(--tile-ico-r, 0); background: var(--tile-ico-bg, none); }
	.tile.warn .ico { background: var(--tile-ico-bg-warn, none); }
</style>
