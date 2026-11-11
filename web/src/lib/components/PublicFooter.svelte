<script lang="ts">
	import { page } from '$app/state';
	import { goToSection } from '$lib/scrollToSection';

	// FHC rebrand: one-page marketing site, so the footer nav mirrors the
	// homepage anchors (not the old marketplace route list). Legal pages
	// (/privacy, /terms) are kept since the disclaimer links to them.
	// See $lib/scrollToSection for why these are ids, not #hash hrefs —
	// this footer is shared across every public route, not just the home.
	const links = [
		{ id: 'approach', label: 'Our approach' },
		{ id: 'how', label: 'How it works' },
		{ id: 'programs', label: 'Programs' },
		{ id: 'about', label: 'About us' }
	];

	// TODO: contact email still to be supplied (handoff README "still to be supplied")
	const contactEmail: string | null = null;

	function nav(id: string) {
		goToSection(id, page.url.pathname);
	}
</script>

<footer class="site-footer">
	<div class="container inner">
		<div class="brand">
			<span class="wordmark">Functional Health Collaborative</span>
			<p class="tagline">Personalised Perimenopause and Menopause Care</p>
		</div>
		<nav class="link-row" aria-label="Footer">
			{#each links as l (l.id)}<a href="/" onclick={(e) => { e.preventDefault(); nav(l.id); }}>{l.label}</a>{/each}
			{#if contactEmail}
				<a href="mailto:{contactEmail}">{contactEmail}</a>
			{:else}
				<span class="todo">[email]</span>
			{/if}
		</nav>
	</div>
	<p class="disclaimer container">
		Our services are complementary and work alongside — not in place of — your GP or medical
		specialist. We do not diagnose or treat medical conditions. Always consult your doctor
		before making changes to medication. See our <a href="/terms">Terms of Service</a> for the
		full disclaimer.
	</p>
	<p class="copyright container">© 2026 Functional Health Collaborative · <a href="/privacy">Privacy policy</a> · <a href="/terms">Terms</a></p>
</footer>

<style>
	.site-footer {
		margin-top: var(--space-7);
		background: var(--pub-navy);
		color: #ffffff;
	}
	.inner { display: flex; flex-wrap: wrap; justify-content: space-between; gap: var(--space-6); padding: var(--space-6) var(--space-5) var(--space-5); }
	.brand { display: flex; flex-direction: column; gap: .5rem; max-width: 22rem; }
	.wordmark { font-family: var(--pub-font-heading); font-weight: 700; font-size: 1.3rem; color: #ffffff; }
	.tagline { margin: 0; font-size: .9rem; color: #cfcfe3; }
	.link-row { display: flex; flex-wrap: wrap; gap: .5rem 1.75rem; align-items: center; font-size: .9375rem; font-weight: 500; }
	.link-row a, .link-row .todo { color: #ffffff; text-decoration: none; }
	.link-row a:hover { text-decoration: underline; }
	.link-row .todo { color: #cfcfe3; font-style: italic; }
	.disclaimer { padding: 0 var(--space-5) var(--space-3); color: #cfcfe3; font-size: .8rem; max-width: 54rem; line-height: 1.6; }
	.disclaimer a { color: #ffffff; text-decoration: underline; }
	.copyright { padding: 0 var(--space-5) var(--space-5); color: #cfcfe3; font-size: .8rem; }
	.copyright a { color: #cfcfe3; text-decoration: underline; }
</style>
