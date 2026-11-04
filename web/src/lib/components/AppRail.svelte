<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { post } from '$lib/api';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';
	import Menu from './Menu.svelte';

	// Ground-up rebuild, direct instruction: keep a sidebar, but don't
	// increment the old one — this is a different object entirely. A
	// narrow, icon-only floating dock (inset from the viewport edge, its
	// own rounded card with a shadow) instead of a flush, full-height,
	// solid-gradient panel. The brand gradient still shows — as a small
	// highlight behind the active/hovered icon, not painted across the
	// whole surface. Tooltips (title attr) replace labels at this width.
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
		<a href={it.href} class:on={isActive(it.href)} title="{it.label}{it.locked ? ' (Pro)' : ''}" aria-label={it.label}>
			<Icon name={it.icon} size={19} />
			{#if it.locked}<span class="lock" aria-hidden="true">★</span>{/if}
			{#if it.badge}<span class="badge">{it.badge > 99 ? '99+' : it.badge}</span>{/if}
		</a>
	</li>
{/snippet}

<nav class="dock" aria-label="{portalLabel} navigation">
	<a href="/" class="mark" aria-label="Functional Health Collab home" title="Functional Health Collab">
		<Sprig size={20} />
	</a>

	{#if onCommandPalette}
		<button class="dock-btn search-trigger" onclick={onCommandPalette} title="Search" aria-label="Search">
			<Icon name="search" size={17} />
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
			<a class="dock-btn switcher" href={switcherTo === 'admin' ? '/admin' : '/practitioner/dashboard'} title="{switcherTo === 'admin' ? 'Switch to admin view' : 'Switch to practitioner view'}">
				<Icon name="switch" size={17} />
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
	.dock {
		position: sticky; top: var(--space-5); align-self: flex-start;
		height: calc(100dvh - var(--space-5) * 2);
		width: 4.5rem; flex: 0 0 auto;
		display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
		padding: var(--space-3) 0; margin-left: var(--space-5);
		background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-xl);
		box-shadow: var(--shadow-lg); z-index: 40; overflow-y: auto;
	}
	.mark {
		display: flex; align-items: center; justify-content: center; width: 2.6rem; height: 2.6rem;
		border-radius: var(--r-lg); color: #fff; text-decoration: none; margin-bottom: var(--space-2);
		background: linear-gradient(135deg, var(--rail-top), var(--rail-bottom));
	}
	.dock-btn {
		display: flex; align-items: center; justify-content: center; width: 2.6rem; height: 2.6rem;
		border-radius: var(--r-lg); border: none; background: none; color: var(--ink-2);
		cursor: pointer; text-decoration: none;
	}
	.dock-btn:hover { background: var(--panel-2); color: var(--ink); }
	hr { border: none; border-top: 1px solid var(--line); width: 2rem; margin: var(--space-1) 0; }
	.group { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .3rem; align-items: center; }
	li a {
		display: flex; align-items: center; justify-content: center; width: 2.6rem; height: 2.6rem;
		color: var(--ink-2); text-decoration: none; border-radius: var(--r-lg); position: relative;
	}
	li a:hover { background: var(--panel-2); color: var(--ink); }
	.lock { position: absolute; top: -.2rem; right: -.1rem; font-size: .6rem; line-height: 1; color: var(--warn); }
	.badge {
		position: absolute; top: -.25rem; right: -.25rem; min-width: 1.05rem; height: 1.05rem;
		padding: 0 .25rem; border-radius: 99px; background: var(--danger);
		color: #fff; font-size: .6rem; font-weight: 700; line-height: 1.05rem; text-align: center;
		box-shadow: 0 0 0 2px var(--panel);
	}
	li a.on {
		color: #fff;
		background: linear-gradient(135deg, var(--rail-top), var(--rail-bottom));
		box-shadow: var(--shadow);
	}
	.foot { margin-top: auto; display: flex; flex-direction: column; align-items: center; gap: .2rem; }
	.foot :global(.menu-wrap .icon-btn) {
		width: 2.6rem; height: 2.6rem; border-radius: var(--r-lg); color: var(--ink-2);
	}
	.foot :global(.menu-wrap .icon-btn:hover) { background: var(--panel-2); color: var(--ink); }
	.foot :global(.menu-wrap .menu-pop) { left: 100%; right: auto; bottom: 0; top: auto; margin: 0 0 0 .5rem; }
	.who-row { display: flex; align-items: center; gap: .5rem; padding: .5rem .6rem; font-size: var(--text-sm); color: var(--muted); white-space: nowrap; }
	@media (max-width: 860px) {
		.dock {
			position: fixed; bottom: var(--space-3); top: auto; left: var(--space-3); right: var(--space-3);
			margin-left: 0; height: auto; width: auto; flex-direction: row; justify-content: space-around;
			padding: var(--space-2); overflow: visible;
		}
		.mark, hr, .search-trigger, .switcher { display: none; }
		.group { flex-direction: row; }
		.foot { margin-top: 0; }
		.foot :global(.menu-wrap .menu-pop) { left: auto; right: 0; bottom: 100%; margin: 0 0 .5rem; }
	}
</style>
