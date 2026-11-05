<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';
	import { currentSession, LANDING } from '$lib/session';

	// Flat white bar now, matching the portal dock's language (a small
	// gradient badge behind the logo only, not a full-width painted
	// band) — part of the ground-up pass retiring every surface that
	// used to paint the brand gradient across its whole area.
	const links = [
		{ href: '/practitioners', label: 'Find a practitioner' },
		{ href: '/join', label: 'For practitioners' },
		{ href: '/pricing', label: 'Pricing' },
		{ href: '/faq', label: 'FAQ' }
	];

	// Real bug, not cosmetic: this nav always showed "Log in"/"Get started"
	// even to an already-authenticated visitor (the session cookie was
	// valid the whole time — `/api/auth/me` returns 200 — the nav just
	// never checked). Read as "why do I need to log in again."
	let session = $state<{ role: string } | null>(null);
	let checked = $state(false);
	onMount(async () => {
		session = await currentSession();
		checked = true;
	});

	let mobileOpen = $state(false);
</script>

<header class="topbar">
	<div class="inner container">
		<a href="/" class="brand">
			<span class="mark"><Sprig size={18} /></span>
			<span class="wordmark">Functional Health Collab</span>
		</a>
		<nav class="links" aria-label="Main">
			{#each links as l (l.href)}
				<a href={l.href} class:on={page.url.pathname === l.href}>{l.label}</a>
			{/each}
		</nav>
		<div class="cta">
			{#if checked}
				{#if session}
					<a href={LANDING[session.role] ?? '/account'} class="btn filled">Dashboard</a>
				{:else}
					<a href="/login" class="ghostlink">Log in</a>
					<a href="/signup" class="btn filled">Get started</a>
				{/if}
			{/if}
		</div>
		<button class="hamburger" onclick={() => (mobileOpen = !mobileOpen)} aria-label="Open menu" aria-expanded={mobileOpen}>
			<Icon name={mobileOpen ? 'x' : 'menu'} size={20} />
		</button>
	</div>

	{#if mobileOpen}
		<nav class="mobile-sheet" aria-label="Main">
			{#each links as l (l.href)}
				<a href={l.href} class:on={page.url.pathname === l.href} onclick={() => (mobileOpen = false)}>{l.label}</a>
			{/each}
			<a href="/contact" onclick={() => (mobileOpen = false)}>Contact</a>
			<hr />
			{#if checked}
				{#if session}
					<a href={LANDING[session.role] ?? '/account'} class="sheet-cta">Dashboard</a>
				{:else}
					<a href="/login" onclick={() => (mobileOpen = false)}>Log in</a>
					<a href="/signup" class="sheet-cta" onclick={() => (mobileOpen = false)}>Get started</a>
				{/if}
			{/if}
		</nav>
	{/if}
</header>

<style>
	.topbar {
		position: sticky; top: 0; z-index: 40; background: var(--panel); background-image: var(--glass-sheen);
		border-bottom: 1px solid var(--glass-border);
		backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur);
	}
	.inner { display: flex; align-items: center; gap: var(--space-6); padding: var(--space-3) var(--space-5); min-height: 3.75rem; }
	.brand { display: flex; align-items: center; gap: .6rem; color: var(--ink); text-decoration: none; font-weight: 750; font-size: var(--text-base); }
	.mark {
		display: flex; align-items: center; justify-content: center; width: 2rem; height: 2rem;
		border-radius: var(--r); color: #fff;
		background: linear-gradient(135deg, var(--rail-top), var(--rail-bottom));
	}
	.links { display: flex; gap: var(--space-4); margin-right: auto; }
	.links a { color: var(--ink-2); text-decoration: none; font-size: var(--text-sm); font-weight: 650; padding: .4rem .2rem; }
	.links a.on, .links a:hover { color: var(--accent-ink); }
	.cta { display: flex; align-items: center; gap: var(--space-4); min-height: 2.2rem; }
	.ghostlink { color: var(--ink-2); text-decoration: none; font-size: var(--text-sm); font-weight: 650; }
	.btn.filled {
		background: var(--accent); color: #fff; padding: .5rem 1.1rem; border-radius: var(--r);
		text-decoration: none; font-size: var(--text-sm); font-weight: 750;
	}
	.btn.filled:hover { background: var(--accent-ink); }
	.hamburger { display: none; color: var(--ink); background: none; border: none; cursor: pointer; padding: .4rem; }
	.mobile-sheet { display: flex; flex-direction: column; gap: .1rem; padding: var(--space-2) var(--space-4) var(--space-4); }
	.mobile-sheet a {
		color: var(--ink-2); text-decoration: none; padding: .65rem .6rem; border-radius: var(--r);
		font-size: var(--text-sm); font-weight: 650;
	}
	.mobile-sheet a:hover, .mobile-sheet a.on { background: var(--panel-2); color: var(--accent-ink); }
	.mobile-sheet hr { border: none; border-top: 1px solid var(--line); margin: .4rem 0; }
	.mobile-sheet .sheet-cta { background: var(--accent); color: #fff; font-weight: 750; text-align: center; }
	@media (max-width: 760px) {
		.links, .cta { display: none; }
		.hamburger { display: flex; }
	}
</style>
