<script lang="ts">
	import { page } from '$app/state';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';

	interface NavItem { href: string; label: string; icon: string }
	let { items, portalLabel, userLabel }: { items: NavItem[]; portalLabel: string; userLabel?: string } = $props();
</script>

<!-- Redesigned nav: a slim fixed icon rail (not a full labeled sidebar) —
     keeps the gradient identity, but the shell is genuinely restructured:
     icons + tooltips at rest, label revealed on hover/focus, content column
     gets the width back instead of losing 14.5rem to a permanent sidebar. -->
<nav class="rail" aria-label="{portalLabel} navigation">
	<a href="/" class="mark" aria-label="Clinic home"><Sprig size={22} /></a>
	<ul>
		{#each items as it (it.href)}
			<li>
				<a href={it.href} class:on={page.url.pathname === it.href || page.url.pathname.startsWith(it.href + '/')} title={it.label}>
					<span class="ic"><Icon name={it.icon} /></span>
					<span class="lbl">{it.label}</span>
				</a>
			</li>
		{/each}
	</ul>
	<div class="foot">
		<span class="poc-tag" title="Phase 4 POC">P4</span>
		{#if userLabel}<span class="who">{userLabel}</span>{/if}
		<form method="post" action="/api/auth/logout" onsubmit={(e) => e.preventDefault()}>
			<a href="/login" class="logout" title="Sign out">⏻</a>
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
	ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .35rem; width: 100%; }
	li a {
		display: flex; align-items: center; gap: .6rem; color: #f7dfe2; text-decoration: none;
		padding: .6rem 0; justify-content: center; position: relative; font-size: var(--text-sm);
	}
	.ic { display: flex; }
	.lbl {
		position: absolute; left: 100%; margin-left: .5rem; background: var(--ink); color: #fff;
		padding: .3rem .6rem; border-radius: var(--r); white-space: nowrap; font-size: var(--text-xs);
		opacity: 0; pointer-events: none; transition: opacity .12s var(--ease); box-shadow: var(--shadow);
	}
	li a:hover .lbl, li a:focus-visible .lbl { opacity: 1; }
	li a.on { color: #fff; }
	li a.on::before {
		content: ''; position: absolute; left: 0; top: .3rem; bottom: .3rem; width: 3px;
		background: #ff8fa3; border-radius: 2px;
	}
	.foot { margin-top: auto; display: flex; flex-direction: column; align-items: center; gap: .5rem; width: 100%; }
	.who { font-size: var(--text-xs); color: #d9a2aa; writing-mode: vertical-rl; text-orientation: mixed; max-height: 6rem; overflow: hidden; }
	.poc-tag {
		font-size: .55rem; font-weight: 700; letter-spacing: .04em;
		background: rgba(255, 255, 255, .14); color: #fff; padding: .15rem .4rem; border-radius: 99px;
	}
	.logout { color: #f7dfe2; text-decoration: none; font-size: 1.1rem; }
	@media (max-width: 720px) {
		.rail { position: fixed; bottom: 0; top: auto; width: 100%; height: auto; flex-direction: row; padding: .5rem; }
		ul { flex-direction: row; justify-content: space-around; }
		.mark, .foot { display: none; }
	}
</style>
