<script lang="ts">
	import { page } from '$app/state';
	import Icon from './Icon.svelte';
	import BrandMark from './BrandMark.svelte';
	import { goToSection } from '$lib/scrollToSection';

	// Single-practice marketing nav (FHC rebrand): the old nav routed to
	// marketplace pages (/practitioners, /join, /signup, /login); this one
	// scrolls to sections of the one-page homepage, per the handoff — see
	// $lib/scrollToSection for why these are ids, not #hash hrefs.
	const links = [
		{ id: 'approach', label: 'Our approach' },
		{ id: 'how', label: 'How it works' },
		{ id: 'programs', label: 'Programs' },
		{ id: 'about', label: 'About us' }
	];

	let mobileOpen = $state(false);

	function nav(id: string) {
		goToSection(id, page.url.pathname);
	}
</script>

<header class="topbar">
	<div class="inner container">
		<a href="/" class="brand">
			<span class="mark"><BrandMark size={32} /></span>
			<span class="lockup">
				<span class="wordmark">Functional Health Collaborative</span>
				<span class="tagline">Personalised Perimenopause and Menopause Care</span>
			</span>
		</a>
		<nav class="links" aria-label="Main">
			{#each links as l (l.id)}
				<a href="/" onclick={(e) => { e.preventDefault(); nav(l.id); }}>{l.label}</a>
			{/each}
		</nav>
		<div class="cta">
			<a href="/" class="btn filled" onclick={(e) => { e.preventDefault(); nav('book'); }}>Book a free intro call</a>
		</div>
		<button class="hamburger" onclick={() => (mobileOpen = !mobileOpen)} aria-label="Open menu" aria-expanded={mobileOpen}>
			<Icon name={mobileOpen ? 'x' : 'menu'} size={20} />
		</button>
	</div>

	{#if mobileOpen}
		<nav class="mobile-sheet" aria-label="Main">
			{#each links as l (l.id)}
				<a href="/" onclick={(e) => { e.preventDefault(); mobileOpen = false; nav(l.id); }}>{l.label}</a>
			{/each}
			<a href="/" class="sheet-cta" onclick={(e) => { e.preventDefault(); mobileOpen = false; nav('book'); }}>Book a free intro call</a>
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
		color: var(--pub-navy); text-decoration: none; font-size: 1rem;
		font-weight: 500;
	}
	.links a:hover { color: var(--pub-burgundy); }
	.cta { display: flex; align-items: center; }
	/* .btn.filled only gets color/background/radius/weight from the global
	   public-shell rule (+layout.svelte) — size/shape has to be set here,
	   since the nav CTA is deliberately smaller (44px) than the hero/CTA
	   primary buttons (52-56px), matching the handoff's nav button. */
	.cta .btn.filled {
		display: inline-flex; align-items: center; justify-content: center;
		min-height: 44px; padding: 0 20px; font-size: 1rem;
	}
	.hamburger { display: none; color: var(--pub-navy); background: none; border: none; cursor: pointer; padding: .4rem; margin-left: auto; }
	.mobile-sheet { display: flex; flex-direction: column; gap: .1rem; padding: var(--space-2) var(--space-4) var(--space-4); background: var(--pub-card-bg); }
	.mobile-sheet a {
		color: var(--pub-navy); text-decoration: none; padding: .65rem .6rem; border-radius: var(--r);
		font-size: 1rem; font-weight: 500;
	}
	.mobile-sheet a:hover { background: var(--pub-warm-grey); }
	.mobile-sheet .sheet-cta {
		display: flex; align-items: center; justify-content: center; min-height: 44px;
		background: var(--pub-copper); color: var(--pub-navy); font-weight: 600;
		text-align: center; border-radius: 999px; margin-top: .4rem;
	}
	@media (max-width: 760px) {
		.links, .cta { display: none; }
		.hamburger { display: flex; }
	}
</style>
