<script lang="ts">
	import Sprig from './Sprig.svelte';

	// specs/v8 §8.2/§8.5 — the "necessary pages" a visitor needs to find
	// but that don't belong in the primary nav (legal/compliance pages,
	// plus pricing/FAQ/contact) live here instead of crowding PublicNav.
	const groups = [
		{
			title: 'Clinic',
			links: [
				{ href: '/practitioners', label: 'Find a practitioner' },
				{ href: '/join', label: 'For practitioners' },
				{ href: '/pricing', label: 'Pricing' },
				{ href: '/faq', label: 'FAQ' },
				{ href: '/contact', label: 'Contact' }
			]
		},
		{
			title: 'Legal',
			links: [
				{ href: '/privacy', label: 'Privacy Policy' },
				{ href: '/terms', label: 'Terms of Service' },
				{ href: '/cookies', label: 'Cookies' }
			]
		}
	];
</script>

<footer class="site-footer">
	<div class="container inner">
		<div class="brand">
			<Sprig size={20} />
			<span>Clinic</span>
		</div>
		{#each groups as g (g.title)}
			<nav aria-label={g.title}>
				<h3>{g.title}</h3>
				<ul>
					{#each g.links as l (l.href)}<li><a href={l.href}>{l.label}</a></li>{/each}
				</ul>
			</nav>
		{/each}
	</div>
	<p class="disclaimer container">
		Clinic is a decision-support tool for licensed practitioners. It is not
		a medical device and does not provide medical advice directly to
		clients — see our <a href="/terms">Terms of Service</a> for the full
		disclaimer.
	</p>
</footer>

<style>
	.site-footer { border-top: 1px solid var(--line); margin-top: var(--space-7); background: var(--panel-2); }
	.inner { display: flex; flex-wrap: wrap; gap: var(--space-6); padding: var(--space-6) var(--space-5); }
	.brand { display: flex; align-items: center; gap: .5rem; font-weight: 700; color: var(--ink); flex: 1 1 10rem; }
	nav h3 { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: .6rem; }
	nav ul { list-style: none; margin: 0; padding: 0; display: grid; gap: .45rem; }
	nav a { color: var(--ink-2); text-decoration: none; font-size: var(--text-sm); }
	nav a:hover { color: var(--accent-ink); }
	.disclaimer { padding: 0 var(--space-5) var(--space-5); color: var(--muted); font-size: var(--text-xs); max-width: 60rem; }
	.disclaimer a { color: var(--muted); text-decoration: underline; }
</style>
