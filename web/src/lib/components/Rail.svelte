<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { post } from '$lib/api';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';
	import LeafField from './LeafField.svelte';

	// specs/v12 — solid deep-slate sidebar: brand header, search field,
	// pill-style nav, and a user card at the bottom. No animation.
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

	const initials = $derived(
		(userLabel ?? '?').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('') || '?'
	);

	async function logout(e: Event) {
		e.preventDefault();
		await post(fetch, '/auth/logout').catch(() => {});
		goto('/login', { invalidateAll: true });
	}
</script>

<nav class="rail" aria-label="Main navigation">
	<!-- specs/v13 — the falling-leaves motif is a requirement of the rail. -->
	<div class="rail-leaves"><LeafField count={12} /></div>
	<a href="/" class="mark" aria-label="Functional Health Collab home">
		<span class="logo"><Sprig size={18} /></span><span class="brand">Functional Health</span>
	</a>

	{#if onCommandPalette}
		<button class="search-trigger" onclick={onCommandPalette} title="Search (⌘K)">
			<Icon name="search" size={15} /><span class="lbl">Search…</span><kbd>⌘K</kbd>
		</button>
	{/if}

	<ul>
		{#each items as it (it.href)}
			<li>
				<a href={it.href} class:on={isActive(it.href)} title={it.locked ? `${it.label} (Pro)` : it.label} aria-current={isActive(it.href) ? 'page' : undefined}>
					<Icon name={it.icon} size={18} />
					<span class="lbl">{it.label}</span>
					{#if it.locked}<span class="pro">Pro</span>{/if}
					{#if it.badge}<span class="badge">{it.badge > 99 ? '99+' : it.badge}</span>{/if}
				</a>
			</li>
		{/each}
	</ul>

	<div class="foot">
		{#if showSwitcher}
			<a class="icon-item" href={switcherTo === 'admin' ? '/admin' : '/practitioner'}>
				<Icon name="switch" size={17} /><span class="lbl">{switcherTo === 'admin' ? 'Admin view' : 'Practitioner view'}</span>
			</a>
		{/if}
		<div class="user">
			<span class="avatar" aria-hidden="true">{initials}</span>
			{#if userLabel}<span class="who-row" title={userLabel}>{userLabel}</span>{/if}
			<form method="post" action="/api/auth/logout" onsubmit={logout}>
				<button type="submit" class="signout" title="Sign out" aria-label="Sign out"><Icon name="power" size={16} /></button>
			</form>
		</div>
	</div>
</nav>

<style>
	.rail {
		width: var(--rail-w); flex: 0 0 auto; position: sticky; top: 0; height: 100dvh;
		display: flex; flex-direction: column; gap: var(--space-2);
		padding: var(--space-4) var(--space-3); color: var(--rail-ink); z-index: 40;
		background:
			radial-gradient(120% 60% at 0% 0%, color-mix(in srgb, var(--rail-indicator) 22%, transparent), transparent 60%),
			var(--rail-bg);
		isolation: isolate; overflow: hidden;
	}
	.rail-leaves { position: absolute; inset: 0; z-index: 0; --leaf-color: var(--rail-indicator); filter: brightness(1.7) saturate(1.2); }
	.rail > :not(.rail-leaves) { position: relative; z-index: 1; }
	@media (prefers-reduced-motion: reduce) { .rail-leaves { display: none; } }
	.mark { display: flex; align-items: center; gap: .65rem; padding: .25rem .5rem var(--space-3); color: #fff; text-decoration: none; }
	.logo {
		display: inline-flex; align-items: center; justify-content: center; width: 2rem; height: 2rem; border-radius: 9px;
		background: color-mix(in srgb, var(--rail-indicator) 22%, transparent); color: var(--rail-indicator);
	}
	.brand { font-weight: 650; font-size: var(--text-base); letter-spacing: -.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.search-trigger {
		display: flex; align-items: center; gap: .55rem; width: 100%; height: 2.25rem; padding: 0 .65rem; margin-bottom: var(--space-2);
		border: 1px solid rgba(255, 255, 255, .1); border-radius: var(--r); background: rgba(255, 255, 255, .05);
		color: rgba(230, 233, 240, .7); cursor: pointer; font: inherit; text-align: left;
		transition: background var(--duration-fast), border-color var(--duration-fast), color var(--duration-fast);
	}
	.search-trigger .lbl { flex: 1; font-size: var(--text-sm); }
	.search-trigger kbd {
		font: inherit; font-size: .68rem; padding: .05rem .35rem; border-radius: 5px;
		background: rgba(255, 255, 255, .08); color: rgba(230, 233, 240, .65);
	}
	.search-trigger:hover { background: rgba(255, 255, 255, .09); border-color: rgba(255, 255, 255, .18); color: #fff; }
	ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; width: 100%; }
	li a {
		display: flex; align-items: center; gap: .7rem; width: 100%; height: 2.35rem; padding: 0 .7rem;
		color: rgba(230, 233, 240, .72); text-decoration: none; position: relative; border-radius: var(--r);
		transition: background var(--duration-fast), color var(--duration-fast);
	}
	li a:hover { background: rgba(255, 255, 255, .06); color: #fff; }
	li a.on {
		background: linear-gradient(90deg, color-mix(in srgb, var(--rail-indicator) 24%, transparent), rgba(255, 255, 255, .06));
		color: #fff; box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .08);
	}
	li a.on::before {
		content: ''; position: absolute; left: -.5rem; top: .45rem; bottom: .45rem; width: 3px;
		border-radius: 0 3px 3px 0; background: var(--rail-indicator);
	}
	li a.on :global(svg) { color: var(--rail-indicator); }
	.lbl { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--text-sm); font-weight: 500; }
	.pro {
		font-size: .62rem; font-weight: 600; padding: .05rem .4rem; border-radius: 99px;
		background: rgba(255, 255, 255, .1); color: rgba(230, 233, 240, .75);
	}
	.badge {
		flex: 0 0 auto; min-width: 1.1rem; height: 1.1rem; padding: 0 .3rem; border-radius: 99px;
		background: var(--danger); color: #fff; font-size: .62rem; font-weight: 700; line-height: 1.1rem; text-align: center;
	}
	.foot { margin-top: auto; display: flex; flex-direction: column; gap: var(--space-2); width: 100%; }
	.icon-item {
		display: flex; align-items: center; gap: .7rem; width: 100%; height: 2.25rem; padding: 0 .7rem; border-radius: var(--r);
		color: rgba(230, 233, 240, .72); text-decoration: none;
	}
	.icon-item:hover { background: rgba(255, 255, 255, .06); color: #fff; }
	.user {
		display: flex; align-items: center; gap: .6rem; padding: .55rem .6rem; border-radius: 10px;
		background: rgba(255, 255, 255, .05); border: 1px solid rgba(255, 255, 255, .07);
	}
	.avatar {
		flex: 0 0 auto; width: 2rem; height: 2rem; border-radius: 50%; display: grid; place-items: center;
		background: color-mix(in srgb, var(--rail-indicator) 28%, transparent); color: #fff; font-size: .72rem; font-weight: 650;
	}
	.who-row { flex: 1; min-width: 0; font-size: var(--text-sm); font-weight: 500; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.user form { margin: 0; margin-left: auto; }
	.signout {
		display: grid; place-items: center; width: 1.9rem; height: 1.9rem; border: none; border-radius: 7px;
		background: none; color: rgba(230, 233, 240, .6); cursor: pointer;
	}
	.signout:hover { background: rgba(255, 255, 255, .1); color: #fff; }
	:focus-visible { outline-color: var(--rail-indicator); }
	@media (max-width: 760px) {
		.rail {
			position: fixed; bottom: 0; top: auto; left: 0; right: 0; width: 100%; height: auto;
			flex-direction: row; align-items: center; padding: 0; gap: 0; border-right: none; border-top: 1px solid rgba(255, 255, 255, .08);
		}
		.rail-leaves { display: none; }
		.mark, .search-trigger .lbl, .search-trigger kbd, .who-row, .avatar, .icon-item .lbl, li a .pro { display: none; }
		.search-trigger { width: 2.8rem; height: 2.8rem; margin: 0; padding: 0; justify-content: center; border: none; background: none; flex: 0 0 auto; }
		ul { flex-direction: row; justify-content: space-around; }
		li a { flex-direction: column; justify-content: center; gap: .15rem; height: 3.4rem; width: auto; padding: 0 .5rem; border-radius: 0; }
		li a.on { background: none; }
		li a.on::before { left: .4rem; right: .4rem; top: 0; bottom: auto; width: auto; height: 3px; border-radius: 0 0 3px 3px; }
		li a .lbl { flex: none; font-size: .62rem; }
		.badge { position: absolute; top: .2rem; right: .2rem; }
		.foot { margin-top: 0; flex-direction: row; width: auto; gap: 0; }
		.user { padding: 0; background: none; border: none; }
		.icon-item { width: 2.8rem; height: 3rem; justify-content: center; padding: 0; }
		.signout { width: 2.8rem; height: 3rem; }
	}
</style>
