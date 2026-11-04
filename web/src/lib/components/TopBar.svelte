<script lang="ts">
	import { goto } from '$app/navigation';
	import { post } from '$lib/api';
	import Icon from './Icon.svelte';

	// specs/v8 §5.2 — a persistent top bar, genuinely new (today none of
	// the three portals has one). Breadcrumb on the left, the search/
	// command-palette trigger promoted here from its easy-to-miss rail
	// icon, and the portal switcher + sign-out moved up from the rail
	// footer into a more conventional, more discoverable corner.
	let {
		crumbs = [],
		onCommandPalette,
		userLabel,
		showSwitcher = false,
		switcherTo = 'practitioner'
	}: {
		crumbs?: { label: string; href?: string }[];
		onCommandPalette?: () => void;
		userLabel?: string;
		showSwitcher?: boolean;
		switcherTo?: 'admin' | 'practitioner';
	} = $props();

	async function logout(e: Event) {
		e.preventDefault();
		await post(fetch, '/auth/logout').catch(() => {});
		goto('/login', { invalidateAll: true });
	}
</script>

<header class="topbar">
	<nav class="crumbs" aria-label="Breadcrumb">
		{#each crumbs as c, i (c.label)}
			{#if i > 0}<span class="sep" aria-hidden="true">/</span>{/if}
			{#if c.href && i < crumbs.length - 1}
				<a href={c.href}>{c.label}</a>
			{:else}
				<span class="current">{c.label}</span>
			{/if}
		{/each}
	</nav>

	{#if onCommandPalette}
		<button class="search-trigger" onclick={onCommandPalette} aria-label="Search (⌘K)">
			<Icon name="search" size={16} />
			<span>Search…</span>
			<kbd>⌘K</kbd>
		</button>
	{/if}

	<div class="right">
		{#if showSwitcher}
			<a class="switcher" href={switcherTo === 'admin' ? '/admin' : '/practitioner/dashboard'}>
				<Icon name="switch" size={15} />
				{switcherTo === 'admin' ? 'Admin view' : 'Practitioner view'}
			</a>
		{/if}
		{#if userLabel}<span class="who">{userLabel}</span>{/if}
		<form method="post" action="/api/auth/logout" onsubmit={logout}>
			<button type="submit" class="logout" title="Sign out" aria-label="Sign out">⏻</button>
		</form>
	</div>
</header>

<style>
	.topbar {
		position: sticky; top: 0; z-index: 30; height: var(--topbar-h);
		display: flex; align-items: center; gap: var(--space-4);
		padding: 0 var(--space-5); background: var(--panel);
		border-bottom: 1px solid var(--line); box-shadow: var(--shadow);
	}
	.crumbs { display: flex; align-items: center; gap: .4rem; font-size: var(--text-sm); min-width: 0; overflow: hidden; }
	.crumbs a { color: var(--muted); text-decoration: none; white-space: nowrap; }
	.crumbs a:hover { color: var(--accent-ink); }
	.crumbs .current { color: var(--ink); font-weight: 650; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.sep { color: var(--line-2); }
	.search-trigger {
		display: flex; align-items: center; gap: .5rem; margin-left: auto;
		border: 1px solid var(--line-2); border-radius: 99px; background: var(--panel-2);
		color: var(--muted); padding: .4rem .9rem; font: inherit; font-size: var(--text-sm);
		cursor: pointer; min-width: 10rem; max-width: 18rem;
	}
	.search-trigger span { flex: 1 1 auto; text-align: left; }
	.search-trigger:hover, .search-trigger:focus-visible { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-ink); }
	.search-trigger kbd { font-size: .65rem; opacity: .7; border: 1px solid var(--line-2); border-radius: 4px; padding: 0 .3rem; }
	.right { display: flex; align-items: center; gap: var(--space-3); margin-left: var(--space-3); }
	.switcher {
		display: flex; align-items: center; gap: .4rem; color: var(--accent-ink); text-decoration: none;
		font-size: var(--text-sm); font-weight: 650; padding: .35rem .7rem; border-radius: 99px;
		background: var(--accent-soft);
	}
	.who { font-size: var(--text-sm); color: var(--ink-2); white-space: nowrap; }
	.logout { color: var(--muted); font-size: 1.1rem; background: none; border: none; padding: 0; cursor: pointer; line-height: 1; }
	.logout:hover { color: var(--danger); }
	@media (max-width: 720px) {
		.search-trigger span, .who { display: none; }
		.search-trigger { min-width: auto; }
	}
</style>
