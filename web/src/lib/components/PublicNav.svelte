<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import Sprig from './Sprig.svelte';
	import { currentSession, LANDING } from '$lib/session';

	const links = [
		{ href: '/', label: 'Directory' },
		{ href: '/about', label: 'About' },
		{ href: '/join', label: 'For practitioners' }
	];

	// Real bug, not cosmetic: this nav always showed "Log in"/"Get started"
	// even to an already-authenticated visitor (the session cookie was
	// valid the whole time — `/api/auth/me` returns 200 — the nav just
	// never checked). Read as "why do I need to log in again."
	let session = $state<{ role: string } | null>(null);
	// `checked` gates rendering either CTA state until the session check
	// resolves — without it, an already-logged-in visitor still saw (and
	// could click) "Log in" for one round trip on every load, a narrower
	// version of the same bug the fix above already covers for the
	// *permanent* case (specs/v4/04-known-issues.md#m17).
	let checked = $state(false);
	onMount(async () => {
		session = await currentSession();
		checked = true;
	});
</script>

<header class="topbar">
	<div class="inner container">
		<a href="/" class="brand">
			<Sprig size={22} />
			<span class="wordmark">Clinic</span>
		</a>
		<nav aria-label="Main">
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
	</div>
</header>

<style>
	.topbar {
		position: sticky; top: 0; z-index: 40; background: var(--glass);
		-webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);
		border-bottom: 1px solid var(--glass-line);
	}
	.inner { display: flex; align-items: center; gap: var(--space-6); padding: var(--space-3) var(--space-5); }
	.brand { display: flex; align-items: center; gap: .5rem; color: var(--ink); text-decoration: none; font-weight: 700; font-size: var(--text-lg); }
	nav { display: flex; gap: var(--space-5); margin-right: auto; }
	nav a { color: var(--ink-2); text-decoration: none; font-size: var(--text-sm); font-weight: 600; }
	nav a.on { color: var(--accent-ink); }
	.cta { display: flex; align-items: center; gap: var(--space-4); min-height: 2.2rem; }
	.ghostlink { color: var(--ink-2); text-decoration: none; font-size: var(--text-sm); font-weight: 600; }
	.btn.filled {
		background: var(--accent); color: #fff; padding: .5rem 1rem; border-radius: 99px;
		text-decoration: none; font-size: var(--text-sm); font-weight: 700;
	}
	@media (max-width: 720px) { nav { display: none; } }
</style>
