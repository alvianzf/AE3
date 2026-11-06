<script lang="ts">
	import Sprig from './Sprig.svelte';

	// specs/v8 §8.2/§8.5 — the "necessary pages" a visitor needs to find
	// but that don't belong in the primary nav (legal/compliance pages,
	// plus pricing/FAQ/contact) live here instead of crowding PublicNav.
	const groups = [
		{
			title: 'Functional Health Collab',
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
			<span>Functional Health Collab</span>
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
		Functional Health Collab is a decision-support tool for licensed practitioners. It is not
		a medical device and does not provide medical advice directly to
		clients — see our <a href="/terms">Terms of Service</a> for the full
		disclaimer.
	</p>
</footer>

<style>
	.site-footer {
		border-top: 1px solid rgba(45, 106, 79, 0.15);
		margin-top: var(--space-7);
		background: #f4f6f0;
	}
	.inner { display: flex; flex-wrap: wrap; gap: var(--space-6); padding: var(--space-6) var(--space-5); }
	.brand {
		display: flex; align-items: center; gap: .6rem;
		font-weight: 700; color: #1b4332; flex: 1 1 10rem;
		background: none; border: none; box-shadow: none;
	}
	.brand :global(svg) { color: #2d6a4f; }
	nav h3 { font-size: var(--text-xs); letter-spacing: .06em; color: #52796f; margin-bottom: .6rem; text-transform: uppercase; font-weight: 700; }
	nav ul { list-style: none; margin: 0; padding: 0; display: grid; gap: .45rem; }
	nav a { color: #2d3748; text-decoration: none; font-size: var(--text-sm); font-weight: 500; transition: color .15s ease; }
	nav a:hover { color: #2d6a4f; }
	.disclaimer { padding: 0 var(--space-5) var(--space-5); color: #52796f; font-size: var(--text-xs); max-width: 60rem; line-height: 1.6; }
	.disclaimer a { color: #2d6a4f; text-decoration: underline; }
</style>
