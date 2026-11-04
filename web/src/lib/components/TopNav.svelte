<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { post } from '$lib/api';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';
	import Menu from './Menu.svelte';

	// Replaces AppRail (vertical icon rail) + TopBar (a second, separate nav
	// surface stacked next to it) with ONE horizontal bar. Direct feedback:
	// a rail-on-the-left plus a bar-on-top was still two navigation
	// surfaces to scan, which read as "the same confusing layout" even
	// after the rail itself got labels. One bar, one scan line.
	interface NavItem { href: string; label: string; icon: string; locked?: boolean; badge?: number; navGroup?: 'primary' | 'secondary' }
	let {
		items, portalLabel, userLabel, onCommandPalette,
		showSwitcher = false, switcherTo = 'practitioner'
	}: {
		items: NavItem[]; portalLabel: string; userLabel?: string; onCommandPalette?: () => void;
		showSwitcher?: boolean; switcherTo?: 'admin' | 'practitioner';
	} = $props();

	const primary = $derived(items.filter((i) => i.navGroup === 'primary'));
	const secondary = $derived(items.filter((i) => i.navGroup !== 'primary'));

	function isActive(href: string): boolean {
		const path = page.url.pathname;
		if (path !== href && !path.startsWith(href + '/')) return false;
		return !items.some(
			(other) =>
				other.href !== href && other.href.length > href.length &&
				(path === other.href || path.startsWith(other.href + '/'))
		);
	}

	let mobileOpen = $state(false);

	async function logout(e: Event) {
		e.preventDefault();
		await post(fetch, '/auth/logout').catch(() => {});
		goto('/login', { invalidateAll: true });
	}
</script>

{#snippet tab(it: NavItem)}
	<a href={it.href} class="tab" class:on={isActive(it.href)} title={it.locked ? `${it.label} (Pro)` : it.label}>
		<Icon name={it.icon} size={16} />
		<span class="lbl">{it.label}</span>
		{#if it.locked}<span class="pro">Pro</span>{/if}
		{#if it.badge}<span class="badge">{it.badge > 99 ? '99+' : it.badge}</span>{/if}
	</a>
{/snippet}

<header class="topnav">
	<div class="row">
		<a href="/" class="brand" aria-label="Functional Health Collab home">
			<Sprig size={20} />
			<span class="wordmark">Functional Health Collab</span>
		</a>
		<span class="portal-pill">{portalLabel}</span>

		<nav class="primary-tabs" aria-label="{portalLabel} navigation">
			{#each primary as it (it.href)}{@render tab(it)}{/each}
		</nav>

		<div class="spacer"></div>

		{#if onCommandPalette}
			<button class="search-trigger" onclick={onCommandPalette} aria-label="Search (⌘K)">
				<Icon name="search" size={15} />
				<span>Search…</span>
			</button>
		{/if}

		<!-- Everything else (secondary/account-shaped items, the dual-role
		     switcher, who's signed in, sign out) lives in ONE dropdown
		     instead of competing for bar space — fewer simultaneous
		     affordances on screen than the old rail's full stacked list. -->
		<Menu label="More">
			{#snippet items()}
				{#each secondary as it (it.href)}
					<a href={it.href}><Icon name={it.icon} size={15} /> {it.label}{#if it.locked} <span class="pro-inline">Pro</span>{/if}</a>
				{/each}
				{#if showSwitcher}
					<a href={switcherTo === 'admin' ? '/admin' : '/practitioner/dashboard'}>
						<Icon name="switch" size={15} /> {switcherTo === 'admin' ? 'Switch to admin view' : 'Switch to practitioner view'}
					</a>
				{/if}
				{#if userLabel}<div class="who-row"><Icon name="user-card" size={15} /> {userLabel}</div>{/if}
				<form method="post" action="/api/auth/logout" onsubmit={logout}>
					<button type="submit" class="danger"><Icon name="x" size={15} /> Sign out</button>
				</form>
			{/snippet}
		</Menu>

		<button class="hamburger" onclick={() => (mobileOpen = !mobileOpen)} aria-label="Open navigation" aria-expanded={mobileOpen}>
			<Icon name="menu" size={20} />
		</button>
	</div>

	{#if mobileOpen}
		<nav class="mobile-sheet" aria-label="{portalLabel} navigation">
			{#each [...primary, ...secondary] as it (it.href)}
				<a href={it.href} class:on={isActive(it.href)} onclick={() => (mobileOpen = false)}>
					<Icon name={it.icon} size={17} /> {it.label}
				</a>
			{/each}
			{#if onCommandPalette}
				<button onclick={() => { mobileOpen = false; onCommandPalette?.(); }}><Icon name="search" size={17} /> Search</button>
			{/if}
			{#if showSwitcher}
				<a href={switcherTo === 'admin' ? '/admin' : '/practitioner/dashboard'}>
					<Icon name="switch" size={17} /> {switcherTo === 'admin' ? 'Switch to admin view' : 'Switch to practitioner view'}
				</a>
			{/if}
			<form method="post" action="/api/auth/logout" onsubmit={logout}>
				<button type="submit" class="danger"><Icon name="x" size={17} /> Sign out</button>
			</form>
		</nav>
	{/if}
</header>

<style>
	.topnav {
		position: sticky; top: 0; z-index: 40;
		background: linear-gradient(100deg, var(--rail-top), var(--rail-bottom));
		color: #fdf1f2; box-shadow: var(--shadow);
	}
	.row { display: flex; align-items: center; gap: var(--space-4); padding: 0 var(--space-5); height: 3.75rem; }
	.brand { display: flex; align-items: center; gap: .5rem; color: #fff; text-decoration: none; flex: 0 0 auto; }
	.wordmark { font-weight: 750; font-size: var(--text-base); white-space: nowrap; }
	.portal-pill {
		font-size: .62rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em;
		background: rgba(255, 255, 255, .16); color: #fdf1f2; padding: .25rem .55rem; border-radius: 99px;
		flex: 0 0 auto; white-space: nowrap;
	}
	.primary-tabs { display: flex; align-items: center; gap: .3rem; margin-left: var(--space-3); }
	.tab {
		display: flex; align-items: center; gap: .5rem; color: #f7dfe2; text-decoration: none;
		padding: .5rem .9rem; border-radius: 99px; font-size: var(--text-sm); font-weight: 650;
		position: relative; white-space: nowrap;
	}
	.tab:hover { background: rgba(255, 255, 255, .1); }
	.tab.on { background: rgba(255, 255, 255, .2); color: #fff; }
	.pro { font-size: .6rem; font-weight: 700; text-transform: uppercase; opacity: .8; }
	.pro-inline { font-size: .6rem; font-weight: 700; text-transform: uppercase; opacity: .7; margin-left: .2rem; }
	.badge {
		min-width: 1.1rem; height: 1.1rem; padding: 0 .3rem; border-radius: 99px; background: var(--danger, #b13434);
		color: #fff; font-size: .62rem; font-weight: 700; line-height: 1.1rem; text-align: center;
	}
	.spacer { flex: 1 1 auto; }
	.search-trigger {
		display: flex; align-items: center; gap: .5rem; border: 1px solid rgba(255, 255, 255, .3);
		border-radius: 99px; background: rgba(255, 255, 255, .08); color: #fdf1f2;
		padding: .4rem .9rem; font: inherit; font-size: var(--text-sm); cursor: pointer; flex: 0 0 auto;
	}
	.search-trigger:hover, .search-trigger:focus-visible { background: rgba(255, 255, 255, .18); }
	.row :global(.menu-wrap .icon-btn) {
		color: #fdf1f2; width: 2.2rem; height: 2.2rem; border-radius: 50%;
		display: flex; align-items: center; justify-content: center;
	}
	.row :global(.menu-wrap .icon-btn:hover) { background: rgba(255, 255, 255, .14); }
	.who-row { display: flex; align-items: center; gap: .5rem; padding: .5rem .6rem; font-size: var(--text-sm); color: var(--muted); }
	.hamburger { display: none; color: #fdf1f2; background: none; border: none; cursor: pointer; padding: .4rem; }
	.mobile-sheet {
		display: flex; flex-direction: column; gap: .1rem; padding: var(--space-2) var(--space-4) var(--space-4);
		background: linear-gradient(180deg, var(--rail-top), var(--rail-bottom));
	}
	.mobile-sheet a, .mobile-sheet button {
		display: flex; align-items: center; gap: .7rem; color: #f7dfe2; text-decoration: none;
		padding: .65rem .6rem; border-radius: var(--r); font-size: var(--text-sm); font-weight: 600;
		background: none; border: none; font-family: inherit; text-align: left; cursor: pointer;
	}
	.mobile-sheet a:hover, .mobile-sheet button:hover { background: rgba(255, 255, 255, .1); }
	.mobile-sheet a.on { background: rgba(255, 255, 255, .2); color: #fff; }
	.mobile-sheet button.danger { color: #ffb4b4; }
	@media (max-width: 880px) {
		.primary-tabs .lbl { display: none; }
		.search-trigger span { display: none; }
	}
	@media (max-width: 680px) {
		.primary-tabs, .search-trigger, .row :global(.menu-wrap) { display: none; }
		.hamburger { display: flex; }
		.wordmark { display: none; }
	}
</style>
