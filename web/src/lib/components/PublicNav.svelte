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
			<span class="mark"><Sprig size={22} /></span>
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
					<a href="/signup" class="btn filled">Sign up as a client</a>
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
					<a href="/signup" class="sheet-cta" onclick={() => (mobileOpen = false)}>Sign up as a client</a>
				{/if}
			{/if}
		</nav>
	{/if}
</header>

<style>
	.topbar {
		position: sticky; top: 0; z-index: 40;
		background: rgba(255, 255, 255, 0.92);
		border-bottom: 1px solid rgba(45, 106, 79, 0.12);
		backdrop-filter: blur(20px) saturate(160%);
		-webkit-backdrop-filter: blur(20px) saturate(160%);
	}
	.inner { display: flex; align-items: center; gap: var(--space-6); padding: var(--space-3) var(--space-5); min-height: 3.75rem; }
	.brand {
		display: flex; align-items: center; gap: .6rem;
		color: #1b4332; text-decoration: none;
		font-weight: 750; font-size: var(--text-base);
		letter-spacing: -.02em;
	}
	/* Logo mark has NO boxes, borders, or backgrounds - pure SVG */
	.mark {
		display: inline-flex; align-items: center; justify-content: center;
		color: #2d6a4f; background: none; border: none; box-shadow: none; padding: 0;
	}
	.links { display: flex; gap: var(--space-5); margin-right: auto; }
	.links a {
		position: relative; color: var(--ink-2); text-decoration: none; font-size: var(--text-sm);
		font-weight: 650; padding: .4rem .1rem;
		transition: color var(--duration-fast);
	}
	.links a::after {
		content: ''; position: absolute; left: 0; right: 100%; bottom: -1px; height: 2px;
		background: #2d6a4f; transition: right var(--duration-base) var(--ease);
	}
	.links a.on::after, .links a:hover::after { right: 0; }
	.links a.on, .links a:hover { color: #2d6a4f; }
	.cta { display: flex; align-items: center; gap: var(--space-4); min-height: 2.2rem; }
	.ghostlink { color: var(--ink-2); text-decoration: none; font-size: var(--text-sm); font-weight: 650; }
	.ghostlink:hover { color: #2d6a4f; }
	.btn.filled {
		background: #2d6a4f; color: #fff; padding: .5rem 1.15rem; border-radius: var(--r);
		text-decoration: none; font-size: var(--text-sm); font-weight: 750;
		transition: background var(--duration-fast), transform var(--duration-fast);
	}
	.btn.filled:hover { background: #1b4332; transform: translateY(-1px); }
	.hamburger { display: none; color: #1b4332; background: none; border: none; cursor: pointer; padding: .4rem; margin-left: auto; }
	.mobile-sheet { display: flex; flex-direction: column; gap: .1rem; padding: var(--space-2) var(--space-4) var(--space-4); background: #ffffff; }
	.mobile-sheet a {
		color: var(--ink-2); text-decoration: none; padding: .65rem .6rem; border-radius: var(--r);
		font-size: var(--text-sm); font-weight: 650;
	}
	.mobile-sheet a:hover, .mobile-sheet a.on { background: #e8f4ec; color: #2d6a4f; }
	.mobile-sheet hr { border: none; border-top: 1px solid rgba(45, 106, 79, 0.12); margin: .4rem 0; }
	.mobile-sheet .sheet-cta { background: #2d6a4f; color: #fff; font-weight: 750; text-align: center; }
	@media (max-width: 760px) {
		.links, .cta { display: none; }
		.hamburger { display: flex; }
	}
</style>
