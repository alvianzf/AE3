<script lang="ts">
	import Icon from './Icon.svelte';

	// Single-practice marketing nav (FHC rebrand): the old nav routed to
	// marketplace pages (/practitioners, /join, /signup, /login); this one
	// is in-page anchors on the one-page homepage, per the handoff.
	const links = [
		{ href: '#approach', label: 'Our approach' },
		{ href: '#how', label: 'How it works' },
		{ href: '#programs', label: 'Programs' },
		{ href: '#about', label: 'About us' }
	];

	let mobileOpen = $state(false);
</script>

<header class="topbar">
	<div class="inner container">
		<a href="/#top" class="brand">
			<svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true" class="mark">
				<circle cx="12" cy="16" r="9" fill="none" stroke="var(--pub-navy)" stroke-width="2.2" />
				<circle cx="20" cy="16" r="9" fill="none" stroke="var(--pub-copper)" stroke-width="2.2" />
			</svg>
			<span class="lockup">
				<span class="wordmark">Functional Health Collaborative</span>
				<span class="tagline">Personalised Perimenopause and Menopause Care</span>
			</span>
		</a>
		<nav class="links" aria-label="Main">
			{#each links as l (l.href)}
				<a href={l.href}>{l.label}</a>
			{/each}
		</nav>
		<div class="cta">
			<a href="#book" class="btn filled">Book a free intro call</a>
		</div>
		<button class="hamburger" onclick={() => (mobileOpen = !mobileOpen)} aria-label="Open menu" aria-expanded={mobileOpen}>
			<Icon name={mobileOpen ? 'x' : 'menu'} size={20} />
		</button>
	</div>

	{#if mobileOpen}
		<nav class="mobile-sheet" aria-label="Main">
			{#each links as l (l.href)}
				<a href={l.href} onclick={() => (mobileOpen = false)}>{l.label}</a>
			{/each}
			<a href="#book" class="sheet-cta" onclick={() => (mobileOpen = false)}>Book a free intro call</a>
		</nav>
	{/if}
</header>

<style>
	.topbar {
		position: sticky; top: 0; z-index: 40;
		background: var(--pub-header-bg, #d8d0c5);
		border-bottom: 1px solid var(--pub-warm-grey);
	}
	.inner { display: flex; align-items: center; gap: var(--space-6); padding: var(--space-3) var(--space-5); min-height: 3.75rem; flex-wrap: wrap; }
	.brand {
		display: flex; align-items: center; gap: .6rem;
		color: var(--pub-navy); text-decoration: none;
	}
	.mark { flex-shrink: 0; }
	.lockup { display: flex; flex-direction: column; line-height: 1.15; }
	.wordmark { font-family: var(--pub-font-heading); font-weight: 700; font-size: 1.05rem; letter-spacing: -.01em; color: var(--pub-navy); }
	.tagline { font-size: .72rem; font-weight: 500; color: var(--pub-burgundy); letter-spacing: .02em; }
	.links { display: flex; gap: var(--space-5); margin-right: auto; margin-left: var(--space-6); }
	.links a {
		color: var(--pub-navy); text-decoration: none; font-size: var(--text-sm);
		font-weight: 500;
	}
	.links a:hover { color: var(--pub-burgundy); }
	.cta { display: flex; align-items: center; }
	.hamburger { display: none; color: var(--pub-navy); background: none; border: none; cursor: pointer; padding: .4rem; margin-left: auto; }
	.mobile-sheet { display: flex; flex-direction: column; gap: .1rem; padding: var(--space-2) var(--space-4) var(--space-4); background: var(--pub-card-bg); }
	.mobile-sheet a {
		color: var(--pub-navy); text-decoration: none; padding: .65rem .6rem; border-radius: var(--r);
		font-size: var(--text-sm); font-weight: 500;
	}
	.mobile-sheet a:hover { background: var(--pub-warm-grey); }
	.mobile-sheet .sheet-cta { background: var(--pub-copper); color: var(--pub-navy); font-weight: 600; text-align: center; border-radius: 999px; margin-top: .4rem; }
	@media (max-width: 760px) {
		.links, .cta { display: none; }
		.hamburger { display: flex; }
	}
</style>
