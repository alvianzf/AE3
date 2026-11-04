<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { post } from '$lib/api';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';
	import Menu from './Menu.svelte';

	// Restored per direct instruction: a persistent left sidebar for the
	// three authenticated portals (the public site keeps its own top bar —
	// standard for a marketing site). Label-visible and grouped
	// (primary/secondary + a divider), not the original icon-only+tooltip
	// version — search, the dual-role switcher, and sign-out now live in
	// the sidebar's own footer instead of a separate top bar, so this is
	// the one and only nav surface per portal.
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

	async function logout(e: Event) {
		e.preventDefault();
		await post(fetch, '/auth/logout').catch(() => {});
		goto('/login', { invalidateAll: true });
	}
</script>

{#snippet navItem(it: NavItem)}
	<li>
		<a href={it.href} class:on={isActive(it.href)} title={it.locked ? `${it.label} (Pro)` : it.label}>
			<span class="ic">
				<Icon name={it.icon} />
				{#if it.locked}<span class="lock" aria-hidden="true">★</span>{/if}
				{#if it.badge}<span class="badge">{it.badge > 99 ? '99+' : it.badge}</span>{/if}
			</span>
			<span class="lbl">{it.label}{#if it.locked} <span class="pro">Pro</span>{/if}</span>
		</a>
	</li>
{/snippet}

<nav class="rail" aria-label="{portalLabel} navigation">
	<a href="/" class="mark" aria-label="Functional Health Collab home"><Sprig size={22} /><span class="wordmark">Functional Health Collab</span></a>
	<span class="portal-label">{portalLabel}</span>

	{#if onCommandPalette}
		<button class="search-trigger" onclick={onCommandPalette}>
			<Icon name="search" size={15} /> <span>Search…</span>
		</button>
	{/if}

	<ul class="group">
		{#each primary as it (it.href)}{@render navItem(it)}{/each}
	</ul>
	{#if primary.length && secondary.length}<hr />{/if}
	<ul class="group">
		{#each secondary as it (it.href)}{@render navItem(it)}{/each}
	</ul>

	<div class="foot">
		{#if showSwitcher}
			<a class="switcher" href={switcherTo === 'admin' ? '/admin' : '/practitioner/dashboard'}>
				<Icon name="switch" size={15} /> <span>{switcherTo === 'admin' ? 'Admin view' : 'Practitioner view'}</span>
			</a>
		{/if}
		<Menu label="Account">
			{#snippet items()}
				{#if userLabel}<div class="who-row"><Icon name="user-card" size={15} /> {userLabel}</div>{/if}
				<form method="post" action="/api/auth/logout" onsubmit={logout}>
					<button type="submit" class="danger"><Icon name="x" size={15} /> Sign out</button>
				</form>
			{/snippet}
		</Menu>
	</div>
</nav>

<style>
	.rail {
		position: sticky; top: 0; align-self: flex-start; height: 100dvh;
		width: 14.5rem; flex: 0 0 auto;
		display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-4) var(--space-3);
		background: linear-gradient(180deg, var(--rail-top), var(--rail-bottom));
		color: #fdf1f2; z-index: 40; overflow-y: auto;
	}
	.mark { color: #fff; display: flex; align-items: center; gap: .5rem; padding: .3rem .2rem; text-decoration: none; }
	.wordmark { font-weight: 750; font-size: var(--text-sm); line-height: 1.2; }
	.portal-label {
		font-size: .62rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em;
		color: #f7dfe2; opacity: .75; padding: 0 .2rem;
	}
	.search-trigger {
		display: flex; align-items: center; gap: .55rem; border: 1px solid rgba(255, 255, 255, .25);
		border-radius: var(--r-lg); background: rgba(255, 255, 255, .08); color: #fdf1f2;
		padding: .5rem .6rem; font: inherit; font-size: var(--text-sm); cursor: pointer; margin: .2rem 0;
	}
	.search-trigger:hover, .search-trigger:focus-visible { background: rgba(255, 255, 255, .16); }
	hr { border: none; border-top: 1px solid rgba(255, 255, 255, .18); width: 100%; margin: 0; }
	.group { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .15rem; width: 100%; }
	li a {
		display: flex; align-items: center; gap: .75rem; color: #f7dfe2; text-decoration: none;
		padding: .55rem .6rem; border-radius: var(--r); position: relative; font-size: var(--text-sm);
	}
	li a:hover { background: rgba(255, 255, 255, .08); }
	.ic { display: flex; position: relative; flex: 0 0 auto; }
	.lock { position: absolute; top: -.35rem; right: -.5rem; font-size: .55rem; line-height: 1; color: #ffd76b; }
	.badge {
		position: absolute; top: -.4rem; right: -.55rem; min-width: 1.05rem; height: 1.05rem;
		padding: 0 .25rem; border-radius: 99px; background: var(--danger, #b13434);
		color: #fff; font-size: .6rem; font-weight: 700; line-height: 1.05rem; text-align: center;
		box-shadow: 0 0 0 2px var(--rail-top, transparent);
	}
	.pro { font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; opacity: .8; }
	.lbl { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	li a.on { color: #fff; background: rgba(255, 255, 255, .14); }
	li a.on::before {
		content: ''; position: absolute; left: -.1rem; top: .35rem; bottom: .35rem; width: 3px;
		background: var(--rail-indicator, #ff8fa3); border-radius: 2px;
	}
	.foot { margin-top: auto; display: flex; flex-direction: column; gap: .4rem; width: 100%; }
	.switcher {
		display: flex; align-items: center; gap: .55rem; color: #fff; text-decoration: none;
		padding: .5rem .6rem; border-radius: var(--r-lg); background: rgba(255, 255, 255, .14);
		font-size: var(--text-sm); font-weight: 650;
	}
	.foot :global(.menu-wrap) { width: 100%; }
	.foot :global(.menu-wrap .icon-btn) {
		width: 100%; height: auto; border-radius: var(--r); justify-content: flex-start; gap: .55rem;
		padding: .5rem .6rem; color: #f7dfe2;
	}
	.foot :global(.menu-wrap .icon-btn:hover) { background: rgba(255, 255, 255, .1); }
	.foot :global(.menu-wrap .menu-pop) { left: 0; right: auto; bottom: 100%; top: auto; margin: 0 0 .25rem; }
	.who-row { display: flex; align-items: center; gap: .5rem; padding: .5rem .6rem; font-size: var(--text-sm); color: var(--muted); }
	@media (max-width: 860px) {
		.rail { position: fixed; bottom: 0; top: auto; width: 100%; height: auto; flex-direction: row; align-items: center; padding: .5rem; overflow: visible; }
		.mark, .portal-label, hr, .search-trigger, .switcher { display: none; }
		.group { flex-direction: row; justify-content: space-around; flex: 1 1 auto; }
		.lbl { display: none; }
		li a { flex-direction: column; gap: .2rem; padding: .3rem .5rem; }
		.foot { margin-top: 0; width: auto; flex: 0 0 auto; }
		.foot :global(.menu-wrap .icon-btn) { width: 2.4rem; height: 2.4rem; justify-content: center; }
		.foot :global(.menu-wrap .menu-pop) { left: auto; right: 0; bottom: 100%; margin: 0 0 .25rem; }
	}
</style>
