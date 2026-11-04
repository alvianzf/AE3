<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { post } from '$lib/api';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';
	import Menu from './Menu.svelte';

	// Full rebuild: a flat, dark, icon-only rail — not a gradient-painted
	// panel, not a floating white dock, not a tile launcher. Square
	// corners, no shadow, the accent color used only for the active-item
	// indicator bar. This is the sidebar, brought back per direct
	// instruction, built as a genuinely different object than any prior
	// version.
	interface NavItem { href: string; label: string; icon: string; locked?: boolean; badge?: number }
	let {
		items, onCommandPalette, userLabel,
		showSwitcher = false, switcherTo = 'practitioner'
	}: {
		items: NavItem[]; onCommandPalette?: () => void; userLabel?: string;
		showSwitcher?: boolean; switcherTo?: 'admin' | 'practitioner';
	} = $props();

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

<nav class="rail" aria-label="Main navigation">
	<a href="/" class="mark" aria-label="Functional Health Collab home"><Sprig size={18} /></a>

	<ul>
		{#each items as it (it.href)}
			<li>
				<a href={it.href} class:on={isActive(it.href)} title="{it.label}{it.locked ? ' (Pro)' : ''}" aria-label={it.label}>
					<Icon name={it.icon} size={18} />
					{#if it.locked}<span class="lock" aria-hidden="true">★</span>{/if}
					{#if it.badge}<span class="badge">{it.badge > 99 ? '99+' : it.badge}</span>{/if}
				</a>
			</li>
		{/each}
	</ul>

	<div class="foot">
		{#if onCommandPalette}
			<button class="icon-item search-trigger" onclick={onCommandPalette} title="Search (⌘K)" aria-label="Search">
				<Icon name="search" size={17} />
			</button>
		{/if}
		{#if showSwitcher}
			<a class="icon-item" href={switcherTo === 'admin' ? '/admin' : '/practitioner'} title="{switcherTo === 'admin' ? 'Switch to admin view' : 'Switch to practitioner view'}">
				<Icon name="switch" size={17} />
			</a>
		{/if}
		<Menu label="Account">
			{#snippet items()}
				{#if userLabel}<div class="who-row">{userLabel}</div>{/if}
				<form method="post" action="/api/auth/logout" onsubmit={logout}>
					<button type="submit" class="danger"><Icon name="x" size={15} /> Sign out</button>
				</form>
			{/snippet}
		</Menu>
	</div>
</nav>

<style>
	.rail {
		width: var(--rail-w); flex: 0 0 auto; position: sticky; top: 0; height: 100dvh;
		display: flex; flex-direction: column; align-items: center; gap: var(--space-3);
		padding: var(--space-3) 0; background: var(--rail-bg); color: var(--rail-ink); z-index: 40;
	}
	.mark { color: var(--rail-ink); display: flex; padding: .4rem; margin-bottom: var(--space-2); }
	ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .15rem; width: 100%; }
	li a {
		display: flex; align-items: center; justify-content: center; width: 100%; height: 2.6rem;
		color: var(--rail-ink); opacity: .6; text-decoration: none; position: relative;
		border-left: 3px solid transparent;
	}
	li a:hover { opacity: 1; background: rgba(255, 255, 255, .06); }
	li a.on { opacity: 1; border-left-color: var(--rail-indicator); background: rgba(255, 255, 255, .04); }
	.lock { position: absolute; top: .35rem; right: 1.1rem; font-size: .55rem; color: #ffd76b; }
	.badge {
		position: absolute; top: .3rem; right: 1rem; min-width: 1rem; height: 1rem;
		padding: 0 .2rem; border-radius: 99px; background: var(--danger);
		color: #fff; font-size: .58rem; font-weight: 700; line-height: 1rem; text-align: center;
	}
	.foot { margin-top: auto; display: flex; flex-direction: column; align-items: center; gap: .2rem; width: 100%; }
	.icon-item {
		display: flex; align-items: center; justify-content: center; width: 100%; height: 2.4rem;
		color: var(--rail-ink); opacity: .6; background: none; border: none; cursor: pointer; text-decoration: none;
	}
	.icon-item:hover { opacity: 1; background: rgba(255, 255, 255, .06); }
	.foot :global(.menu-wrap) { width: 100%; }
	.foot :global(.menu-wrap .icon-btn) {
		width: 100%; height: 2.4rem; border-radius: 0; color: var(--rail-ink); opacity: .6;
	}
	.foot :global(.menu-wrap .icon-btn:hover) { opacity: 1; background: rgba(255, 255, 255, .06); }
	.foot :global(.menu-wrap .menu-pop) { left: 100%; right: auto; bottom: 0; top: auto; margin: 0 0 0 .4rem; }
	.who-row { padding: .5rem .6rem; font-size: var(--text-sm); color: var(--muted); white-space: nowrap; }
	@media (max-width: 760px) {
		.rail {
			position: fixed; bottom: 0; top: auto; left: 0; right: 0; width: 100%; height: auto;
			flex-direction: row; align-items: center; padding: 0;
		}
		.mark { display: none; }
		ul { flex-direction: row; justify-content: space-around; }
		li a { height: 3rem; border-left: none; border-top: 3px solid transparent; }
		li a.on { border-left-color: transparent; border-top-color: var(--rail-indicator); }
		.foot { margin-top: 0; flex-direction: row; width: auto; }
		.icon-item, .foot :global(.menu-wrap .icon-btn) { width: 2.8rem; height: 3rem; }
		.foot :global(.menu-wrap .menu-pop) { left: auto; right: 0; bottom: 100%; margin: 0 0 .4rem; }
	}
</style>
