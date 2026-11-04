<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { post } from '$lib/api';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';

	interface NavItem { href: string; label: string; icon: string; locked?: boolean; badge?: number }
	// onCommandPalette — optional (specs/v7/06): a portal that's wired up
	// a CommandPalette.svelte passes a handler here to get a visible
	// trigger button in the rail, not just the Cmd/Ctrl+K shortcut a
	// first-time user has no way to discover on their own. Omitted
	// entirely (not just hidden) for a portal that hasn't adopted this
	// yet, so AppRail's existing behavior for those portals is unchanged.
	let {
		items, portalLabel, userLabel, onCommandPalette
	}: { items: NavItem[]; portalLabel: string; userLabel?: string; onCommandPalette?: () => void } = $props();

	// specs/v4.1/02 — one visual identity per user type. Colors come from
	// --rail-top/--rail-bottom/--rail-indicator, the same CSS custom
	// properties this component already read before role-theming existed
	// — each portal's own +layout.svelte sets them on its .shell wrapper
	// (a plain cascade override, not a second JS-side theming mechanism),
	// so this component stays role-agnostic rather than needing a `role`
	// prop and a color lookup table of its own.

	// specs/v4.1/03 CR1 — the sign-out form used to just preventDefault and
	// never call the endpoint, so the session cookie outlived the click.
	async function logout(e: Event) {
		e.preventDefault();
		await post(fetch, '/auth/logout').catch(() => {});
		goto('/login', { invalidateAll: true });
	}

	// Most-specific href wins, not "any prefix match" — found live: the
	// admin rail's Library item (href '/admin') is a prefix of every
	// other admin route ('/admin/dashboard', '/admin/users', ...), so a
	// plain `pathname.startsWith(href + '/')` lit Library up on every
	// admin page, not just the library page itself.
	function isActive(href: string): boolean {
		const path = page.url.pathname;
		if (path !== href && !path.startsWith(href + '/')) return false;
		return !items.some(
			(other) =>
				other.href !== href && other.href.length > href.length &&
				(path === other.href || path.startsWith(other.href + '/'))
		);
	}
</script>

<!-- Redesigned nav: a slim fixed icon rail (not a full labeled sidebar) —
     keeps the gradient identity, but the shell is genuinely restructured:
     icons + tooltips at rest, label revealed on hover/focus, content column
     gets the width back instead of losing 14.5rem to a permanent sidebar. -->
<nav class="rail" aria-label="{portalLabel} navigation">
	<a href="/" class="mark" aria-label="Clinic home"><Sprig size={22} /></a>
	<span class="portal-label">{portalLabel}</span>
	{#if onCommandPalette}
		<button class="search-trigger" onclick={onCommandPalette} title="Search (⌘K)" aria-label="Open command palette">
			<Icon name="search" size={18} />
		</button>
	{/if}
	<ul>
		{#each items as it (it.href)}
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
		{/each}
	</ul>
	<div class="foot">
		{#if userLabel}<span class="who">{userLabel}</span>{/if}
		<form method="post" action="/api/auth/logout" onsubmit={logout}>
			<button type="submit" class="logout" title="Sign out">⏻</button>
		</form>
	</div>
</nav>

<style>
	.rail {
		position: sticky; top: 0; align-self: flex-start; height: 100dvh; width: 4.75rem; flex: 0 0 auto;
		display: flex; flex-direction: column; align-items: center; gap: var(--space-4); padding: var(--space-4) 0;
		background: linear-gradient(180deg, var(--rail-top), var(--rail-bottom));
		color: #fdf1f2; z-index: 40;
	}
	.mark { color: #fff; display: flex; padding: .4rem; }
	.search-trigger {
		display: flex; align-items: center; justify-content: center;
		width: 2.2rem; height: 2.2rem; border-radius: 50%; border: none;
		background: rgba(255, 255, 255, .12); color: #f7dfe2; cursor: pointer;
		transition: background var(--duration-fast, .12s) var(--ease);
	}
	.search-trigger:hover, .search-trigger:focus-visible { background: rgba(255, 255, 255, .22); }
	.portal-label {
		writing-mode: vertical-rl; text-orientation: mixed; transform: rotate(180deg);
		font-size: .62rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em;
		color: #f7dfe2; opacity: .85; max-height: 5.5rem; overflow: hidden;
	}
	ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .35rem; width: 100%; }
	li a {
		display: flex; align-items: center; gap: .6rem; color: #f7dfe2; text-decoration: none;
		padding: .6rem 0; justify-content: center; position: relative; font-size: var(--text-sm);
	}
	.ic { display: flex; position: relative; }
	.lock {
		position: absolute; top: -.35rem; right: -.5rem; font-size: .55rem; line-height: 1;
		color: #ffd76b;
	}
	.badge {
		position: absolute; top: -.4rem; right: -.55rem; min-width: 1.05rem; height: 1.05rem;
		padding: 0 .25rem; border-radius: 99px; background: var(--danger, #b13434);
		color: #fff; font-size: .6rem; font-weight: 700; line-height: 1.05rem; text-align: center;
		box-shadow: 0 0 0 2px var(--rail-top, transparent);
	}
	.pro {
		font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
		opacity: .8;
	}
	.lbl {
		position: absolute; left: 100%; margin-left: .5rem; background: var(--ink); color: #fff;
		padding: .3rem .6rem; border-radius: var(--r); white-space: nowrap; font-size: var(--text-xs);
		opacity: 0; pointer-events: none; transition: opacity .12s var(--ease); box-shadow: var(--shadow);
	}
	li a:hover .lbl, li a:focus-visible .lbl { opacity: 1; }
	li a.on { color: #fff; }
	li a.on::before {
		content: ''; position: absolute; left: 0; top: .3rem; bottom: .3rem; width: 3px;
		background: var(--rail-indicator, #ff8fa3); border-radius: 2px;
	}
	.foot { margin-top: auto; display: flex; flex-direction: column; align-items: center; gap: .5rem; width: 100%; }
	.who { font-size: var(--text-xs); color: #d9a2aa; writing-mode: vertical-rl; text-orientation: mixed; max-height: 6rem; overflow: hidden; }
	.logout {
		color: #f7dfe2; font-size: 1.1rem; background: none; border: none; padding: 0;
		cursor: pointer; font-family: inherit; line-height: 1;
	}
	@media (max-width: 720px) {
		.rail { position: fixed; bottom: 0; top: auto; width: 100%; height: auto; flex-direction: row; padding: .5rem; }
		ul { flex-direction: row; justify-content: space-around; }
		.mark, .foot { display: none; }
	}
</style>
