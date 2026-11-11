<script lang="ts">
	import PublicNav from '$lib/components/PublicNav.svelte';
	import PublicFooter from '$lib/components/PublicFooter.svelte';
	let { children } = $props();
</script>

<svelte:head>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link
		rel="stylesheet"
		href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700&family=Figtree:wght@400;500;600&display=swap"
	/>
</svelte:head>

<div class="public-shell">
	<PublicNav />
	<main>
		{@render children()}
	</main>
	<PublicFooter />
</div>

<style>
	:global(:root) {
		--pub-navy: #00004c;
		--pub-burgundy: #7a1f3d;
		--pub-copper: #d79351;
		--pub-warm-grey: #e6e4dd;
		--pub-header-bg: #d8d0c5;
		--pub-bg: #f4f2ed;
		--pub-text: #1c1c33;
		--pub-text-muted: #4a4a5e;
		--pub-card-bg: #ffffff;
		--pub-font-heading: 'Bricolage Grotesque', ui-sans-serif, system-ui, sans-serif;
		--pub-font-body: 'Figtree', ui-sans-serif, system-ui, sans-serif;
	}

	.public-shell {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: var(--pub-bg);
		color: var(--pub-text);
		font-family: var(--pub-font-body);
		font-size: 17px;
		line-height: 1.6;
	}

	main {
		flex: 1 0 auto;
		min-height: 70dvh;
	}

	:global(.public-shell h1),
	:global(.public-shell h2),
	:global(.public-shell h3) {
		font-family: var(--pub-font-heading);
	}

	/* Consistent link colors and interactive resets across all public pages */
	:global(.public-shell a) {
		color: var(--pub-burgundy);
	}
	:global(.public-shell a:hover) {
		color: var(--pub-navy);
	}

	/* Consistent card panels across public auth/form pages */
	:global(.public-shell .card-panel) {
		background: var(--pub-card-bg);
		border: 1px solid var(--pub-warm-grey);
		border-radius: 16px;
		box-shadow: 0 4px 24px rgba(0, 0, 76, 0.06);
		overflow: hidden;
	}
	:global(.public-shell .card-panel .ph) {
		padding: var(--space-4) var(--space-5);
		border-bottom: 1px solid var(--pub-warm-grey);
		background: var(--pub-bg);
	}
	:global(.public-shell .card-panel .ph h2) {
		display: flex;
		align-items: center;
		gap: .6rem;
		font-size: var(--text-lg);
		font-weight: 750;
		color: var(--pub-navy);
		margin: 0;
	}
	:global(.public-shell .card-panel .ph h2 :global(svg)) {
		color: var(--pub-burgundy);
	}
	:global(.public-shell .card-panel .pb) {
		padding: var(--space-5);
	}

	/* Primary button overrides for public pages: pill shape, copper fill, navy
	   text, min-height 52px per the style guide's primary-button spec.
	   (Not !important on sizing so a narrower context — e.g. the nav CTA —
	   can still override to a smaller min-height/padding.) */
	:global(.public-shell .btn.filled),
	:global(.public-shell button[type="submit"]) {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-height: 52px;
		padding: 0 28px;
		font-size: 1.0625rem;
		background: var(--pub-copper) !important;
		color: var(--pub-navy) !important;
		text-decoration: none !important;
		border: none !important;
		border-radius: 999px !important;
		font-weight: 600 !important;
		box-shadow: none !important;
		transition: background var(--duration-fast), transform var(--duration-fast) !important;
	}
	:global(.public-shell .btn.filled:hover),
	:global(.public-shell button[type="submit"]:hover) {
		background: #c98540 !important;
		transform: translateY(-1px) !important;
	}
</style>
