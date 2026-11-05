<script lang="ts">
	import type { Snippet } from 'svelte';

	// specs/v13 — the banner at the top of each portal's home page: portal-
	// accent gradient, sprig watermark, a greeting, optional key numbers and
	// primary actions.
	let {
		eyebrow = '',
		title,
		subtitle = '',
		stats = [],
		actions
	}: {
		eyebrow?: string;
		title: string;
		subtitle?: string;
		stats?: { label: string; value: string | number }[];
		actions?: Snippet;
	} = $props();
</script>

<section class="hero leafmark">
	<div class="copy">
		{#if eyebrow}<span class="eyebrow">{eyebrow}</span>{/if}
		<h2>{title}</h2>
		{#if subtitle}<p>{subtitle}</p>{/if}
		{#if actions}<div class="actions">{@render actions()}</div>{/if}
	</div>
	{#if stats.length}
		<dl class="stats">
			{#each stats as s (s.label)}
				<div><dt>{s.label}</dt><dd>{s.value}</dd></div>
			{/each}
		</dl>
	{/if}
</section>

<style>
	.hero {
		display: flex; align-items: center; justify-content: space-between; gap: var(--space-5); flex-wrap: wrap;
		padding: var(--space-6); margin-bottom: var(--space-5); border-radius: 18px; color: #fff;
		background:
			radial-gradient(90% 140% at 100% 0%, rgba(255, 255, 255, .22), transparent 55%),
			linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent-ink) 82%, #000));
		box-shadow: 0 10px 30px color-mix(in srgb, var(--accent) 30%, transparent);
	}
	.copy { position: relative; z-index: 1; max-width: 36rem; }
	.eyebrow { font-size: var(--text-xs); letter-spacing: .12em; text-transform: uppercase; opacity: .8; font-weight: 600; }
	h2 { font-size: 1.9rem; font-weight: 700; letter-spacing: -.025em; margin: .25rem 0 .35rem; line-height: 1.15; }
	p { opacity: .88; font-size: var(--text-base); }
	.actions { display: flex; gap: var(--space-2); flex-wrap: wrap; margin-top: var(--space-4); }
	.actions :global(.btn) { background: #fff; color: var(--accent-ink); border-color: transparent; box-shadow: none; }
	.actions :global(.btn:hover) { background: rgba(255, 255, 255, .88); color: var(--accent-ink); }
	.actions :global(.btn.ghost) { background: rgba(255, 255, 255, .14); color: #fff; }
	.actions :global(.btn.ghost:hover) { background: rgba(255, 255, 255, .24); color: #fff; }
	.stats { position: relative; z-index: 1; display: flex; gap: var(--space-3); margin: 0; }
	.stats div {
		min-width: 6.5rem; padding: .8rem 1rem; border-radius: 14px;
		background: rgba(255, 255, 255, .14); border: 1px solid rgba(255, 255, 255, .2);
	}
	dt { font-size: var(--text-xs); opacity: .85; }
	dd { margin: .1rem 0 0; font-size: 1.6rem; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.1; }
	@media (max-width: 760px) { .hero { padding: var(--space-5); } h2 { font-size: 1.5rem; } .stats { width: 100%; } .stats div { flex: 1; } }
</style>
