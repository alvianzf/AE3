<script lang="ts">
	import { page } from '$app/state';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';

	interface NavItem { href: string; label: string; icon: string; locked?: boolean; badge?: number; navGroup?: 'primary' | 'secondary' }
	// specs/v8 §5.1 — label-visible by default now (not icon-only with a
	// hover tooltip): an icon-only rail needed a tour/tooltip to be
	// legible at all, which was compensating for an information-scent
	// problem at the source instead of fixing it. Items split into a
	// primary group (the portal's actual job-to-be-done) and a secondary
	// group (account/settings-shaped pages), separated by a divider —
	// unmarked items default to secondary.
	let { items, portalLabel }: { items: NavItem[]; portalLabel: string } = $props();

	const primary = $derived(items.filter((i) => i.navGroup === 'primary'));
	const secondary = $derived(items.filter((i) => i.navGroup !== 'primary'));

	// specs/v4.1/02 — one visual identity per user type, via the
	// --rail-top/--rail-bottom/--rail-indicator custom properties each
	// portal's own +layout.svelte sets on its .shell wrapper.

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
	<a href="/" class="mark" aria-label="Clinic home"><Sprig size={22} /><span class="wordmark">Clinic</span></a>
	<span class="portal-label">{portalLabel}</span>
	<ul class="group">
		{#each primary as it (it.href)}{@render navItem(it)}{/each}
	</ul>
	{#if primary.length && secondary.length}<hr />{/if}
	<ul class="group">
		{#each secondary as it (it.href)}{@render navItem(it)}{/each}
	</ul>
</nav>

<style>
	.rail {
		position: sticky; top: 0; align-self: flex-start; height: 100dvh;
		width: var(--rail-w-expanded); flex: 0 0 auto;
		display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-4) var(--space-3);
		background: linear-gradient(180deg, var(--rail-top), var(--rail-bottom));
		color: #fdf1f2; z-index: 40; overflow-y: auto;
	}
	.mark { color: #fff; display: flex; align-items: center; gap: .5rem; padding: .3rem .2rem; text-decoration: none; }
	.wordmark { font-weight: 750; font-size: var(--text-base); }
	.portal-label {
		font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em;
		color: #f7dfe2; opacity: .75; padding: 0 .2rem;
	}
	hr { border: none; border-top: 1px solid rgba(255, 255, 255, .18); width: 100%; margin: 0; }
	.group { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .15rem; width: 100%; }
	li a {
		display: flex; align-items: center; gap: .75rem; color: #f7dfe2; text-decoration: none;
		padding: .55rem .6rem; border-radius: var(--r); position: relative; font-size: var(--text-sm);
	}
	li a:hover { background: rgba(255, 255, 255, .08); }
	.ic { display: flex; position: relative; flex: 0 0 auto; }
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
	.lbl { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	li a.on { color: #fff; background: rgba(255, 255, 255, .14); }
	li a.on::before {
		content: ''; position: absolute; left: -.1rem; top: .35rem; bottom: .35rem; width: 3px;
		background: var(--rail-indicator, #ff8fa3); border-radius: 2px;
	}
	@media (max-width: 720px) {
		.rail { position: fixed; bottom: 0; top: auto; width: 100%; height: auto; flex-direction: row; padding: .5rem; overflow: visible; }
		.mark, .portal-label, hr { display: none; }
		.group { flex-direction: row; justify-content: space-around; }
		.lbl { display: none; }
		li a { flex-direction: column; gap: .2rem; padding: .3rem .5rem; }
	}
</style>
