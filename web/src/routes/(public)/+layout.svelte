<script lang="ts">
	import PublicNav from '$lib/components/PublicNav.svelte';
	import PublicFooter from '$lib/components/PublicFooter.svelte';
	let { children } = $props();
</script>

<div class="public-shell">
	<PublicNav />
	<main>
		{@render children()}
	</main>
	<PublicFooter />
</div>

<style>
	:global(:root) {
		--pub-forest-dark: #1b4332;
		--pub-forest-deep: #0f2b1d;
		--pub-emerald: #2d6a4f;
		--pub-sage-vibrant: #52b788;
		--pub-sage: #74c69d;
		--pub-sage-light: #d8f3dc;
		--pub-linen: #fbfcf9;
		--pub-sage-tint: #f4f8f4;
		--pub-card-bg: #ffffff;
		--pub-border: rgba(45, 106, 79, 0.14);
		--pub-border-strong: rgba(45, 106, 79, 0.28);
		--pub-text: #1b4332;
		--pub-text-muted: #52796f;
	}

	.public-shell {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: #fbfcf9;
		color: #1b4332;
	}

	main {
		flex: 1 0 auto;
		min-height: 70dvh;
	}

	/* Consistent link colors and interactive resets across all public pages */
	:global(.public-shell a) {
		color: #2d6a4f;
	}
	:global(.public-shell a:hover) {
		color: #1b4332;
	}

	/* Consistent card panels across public auth/form pages */
	:global(.public-shell .card-panel) {
		background: #ffffff;
		border: 1px solid rgba(45, 106, 79, 0.14);
		border-radius: 16px;
		box-shadow: 0 4px 24px rgba(27, 67, 50, 0.06);
		overflow: hidden;
	}
	:global(.public-shell .card-panel .ph) {
		padding: var(--space-4) var(--space-5);
		border-bottom: 1px solid rgba(45, 106, 79, 0.1);
		background: #fbfcf9;
	}
	:global(.public-shell .card-panel .ph h2) {
		display: flex;
		align-items: center;
		gap: .6rem;
		font-size: var(--text-lg);
		font-weight: 750;
		color: #1b4332;
		margin: 0;
	}
	:global(.public-shell .card-panel .ph h2 :global(svg)) {
		color: #2d6a4f;
	}
	:global(.public-shell .card-panel .pb) {
		padding: var(--space-5);
	}

	/* Primary button overrides for public pages to ensure crisp botanical styling */
	:global(.public-shell .btn.filled),
	:global(.public-shell button[type="submit"]) {
		background: #2d6a4f !important;
		color: #ffffff !important;
		border: none !important;
		border-radius: 10px !important;
		font-weight: 750 !important;
		box-shadow: 0 2px 8px rgba(45, 106, 79, 0.2) !important;
		transition: background var(--duration-fast), transform var(--duration-fast) !important;
	}
	:global(.public-shell .btn.filled:hover),
	:global(.public-shell button[type="submit"]:hover) {
		background: #1b4332 !important;
		transform: translateY(-1px) !important;
	}
</style>
