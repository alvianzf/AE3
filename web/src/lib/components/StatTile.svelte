<script lang="ts">
	let {
		label,
		value,
		href,
		icon
	}: { label: string; value: string | number; href?: string; icon?: string } = $props();

	const Tag = $derived(href ? 'a' : 'div');
</script>

<svelte:element this={Tag} href={href} class="tile">
	{#if icon}<span class="ico" aria-hidden="true">{icon}</span>{/if}
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
	.ico { font-size: 1.4rem; }
	.val { font-size: var(--text-xl); font-weight: 700; letter-spacing: -.02em; }
	.lbl { font-size: var(--text-xs); color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
</style>
