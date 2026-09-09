<script lang="ts">
	import Icon from './Icon.svelte';

	let {
		label,
		value,
		href,
		icon
	}: { label: string; value: string | number; href?: string; icon?: string } = $props();

	const Tag = $derived(href ? 'a' : 'div');
</script>

<svelte:element this={Tag} href={href} class="tile">
	{#if icon}<span class="ico"><Icon name={icon} size={20} /></span>{/if}
	<div>
		<div class="val">{value}</div>
		<div class="lbl">{label}</div>
	</div>
</svelte:element>

<style>
	.tile {
		display: flex; align-items: center; gap: var(--space-3); padding: var(--space-4);
		background: var(--panel-2); border: 1px solid var(--line); border-radius: var(--r-lg);
		text-decoration: none; color: inherit; animation: fadeIn .4s var(--ease) both;
		transition: border-color .15s var(--ease), transform .15s var(--ease);
	}
	a.tile:hover { border-color: var(--accent); transform: translateY(-2px); }
	.ico { display: inline-flex; color: var(--accent-ink); flex: 0 0 auto; }
	.val { font-size: var(--text-xl); font-weight: 700; letter-spacing: -.02em; }
	.lbl { font-size: var(--text-xs); color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
</style>
