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
				<a href={it.href} class:on={isActive(it.href)} title={it.locked ? `${it.label} (Pro)` : it.label}>
					<Icon name={it.icon} size={18} />
					<span class="lbl">{it.label}{#if it.locked} <span class="pro">Pro</span>{/if}</span>
					{#if it.badge}<span class="badge">{it.badge > 99 ? '99+' : it.badge}</span>{/if}
				</a>
			</li>
		{/each}
	</ul>

	<div class="foot">
		{#if onCommandPalette}
			<button class="icon-item search-trigger" onclick={onCommandPalette} title="Search (⌘K)">
				<Icon name="search" size={17} /><span class="lbl">Search</span>
			</button>
		{/if}
		{#if showSwitcher}
			<a class="icon-item" href={switcherTo === 'admin' ? '/admin' : '/practitioner'}>
				<Icon name="switch" size={17} /><span class="lbl">{switcherTo === 'admin' ? 'Admin view' : 'Practitioner view'}</span>
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
	.mark { color: var(--rail-ink); display: flex; padding: .4rem var(--space-4); margin-bottom: var(--space-2); }
	ul { list-style: none; margin: 0; padding: 0 var(--space-2); display: flex; flex-direction: column; gap: .15rem; width: 100%; }
	li a {
		display: flex; align-items: center; gap: .7rem; width: 100%; height: 2.5rem; padding: 0 .7rem;
		color: var(--rail-ink); opacity: .65; text-decoration: none; position: relative;
		border-left: 3px solid transparent;
	}
	li a:hover { opacity: 1; background: rgba(255, 255, 255, .06); }
	li a.on { opacity: 1; border-left-color: var(--rail-indicator); background: rgba(255, 255, 255, .04); }
	.lbl { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--text-sm); }
	.pro { font-size: .6rem; font-weight: 700; text-transform: uppercase; opacity: .7; }
	.badge {
		flex: 0 0 auto; min-width: 1rem; height: 1rem; padding: 0 .2rem; border-radius: 99px;
		background: var(--danger); color: #fff; font-size: .58rem; font-weight: 700; line-height: 1rem; text-align: center;
	}
	.foot { margin-top: auto; display: flex; flex-direction: column; gap: .15rem; width: 100%; padding: 0 var(--space-2); }
	.icon-item {
		display: flex; align-items: center; gap: .7rem; width: 100%; height: 2.4rem; padding: 0 .7rem;
		color: var(--rail-ink); opacity: .65; background: none; border: none; cursor: pointer; text-decoration: none;
	}
	.icon-item .lbl { font-size: var(--text-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.icon-item:hover { opacity: 1; background: rgba(255, 255, 255, .06); }
	.foot :global(.menu-wrap) { width: 100%; }
	.foot :global(.menu-wrap .menu-trigger) {
		width: 100%; height: 2.4rem; border-radius: 0; color: var(--rail-ink); opacity: .65; justify-content: flex-start; padding: 0 .7rem;
	}
	.foot :global(.menu-wrap .menu-trigger:hover) { opacity: 1; background: rgba(255, 255, 255, .06); }
	.foot :global(.menu-wrap .menu-pop) { left: 100%; right: auto; bottom: 0; top: auto; margin: 0 0 0 .4rem; }
	.who-row { padding: .5rem .6rem; font-size: var(--text-sm); color: var(--muted); white-space: nowrap; }
	@media (max-width: 760px) {
		.rail {
			position: fixed; bottom: 0; top: auto; left: 0; right: 0; width: 100%; height: auto;
			flex-direction: row; align-items: center; padding: 0;
		}
		.mark { display: none; }
		ul { flex-direction: row; justify-content: space-around; padding: 0; }
		li a { flex-direction: column; gap: .15rem; height: 3rem; width: auto; padding: 0 .5rem; border-left: none; border-top: 3px solid transparent; }
		li a.on { border-left-color: transparent; border-top-color: var(--rail-indicator); }
		.lbl { font-size: .62rem; }
		.badge { position: absolute; top: .2rem; right: .2rem; }
		.foot { margin-top: 0; flex-direction: row; width: auto; padding: 0 .5rem; }
		.icon-item .lbl { display: none; }
		.icon-item, .foot :global(.menu-wrap .menu-trigger) { width: 2.8rem; height: 3rem; justify-content: center; padding: 0; }
		.foot :global(.menu-wrap .menu-pop) { left: auto; right: 0; bottom: 100%; margin: 0 0 .4rem; }
	}
</style>
