<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { post } from '$lib/api';
	import Sprig from './Sprig.svelte';
	import Icon from './Icon.svelte';
	import LeafField from './LeafField.svelte';

	// specs/v12 & v15 — desktop solid deep-slate sidebar + mobile responsive navigation:
	// on mobile screens (<= 760px), bottom bar displays important/primary menus only,
	// while a burger button opens a slide-in side drawer containing the full menu,
	// user profile, search trigger, and session controls.
	export interface NavItem {
		href: string;
		label: string;
		icon: string;
		locked?: boolean;
		badge?: number;
		primary?: boolean;
	}

	let {
		items, onCommandPalette, userLabel,
		showSwitcher = false, switcherTo = 'practitioner'
	}: {
		items: NavItem[]; onCommandPalette?: () => void; userLabel?: string;
		showSwitcher?: boolean; switcherTo?: 'admin' | 'practitioner';
	} = $props();

	let drawerOpen = $state(false);
	let drawerSheetEl = $state<HTMLElement>();
	let burgerBtnEl = $state<HTMLButtonElement>();

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

	// Primary items for mobile bottom bar (top 3 important items)
	const primaryItems = $derived.by(() => {
		const explicit = items.filter((i) => i.primary);
		if (explicit.length > 0) return explicit.slice(0, 3);
		return items.slice(0, 3);
	});

	// Items not displayed in the bottom bar (accessed via drawer)
	const secondaryItems = $derived.by(() => {
		const primaryHrefs = new Set(primaryItems.map((i) => i.href));
		return items.filter((i) => !primaryHrefs.has(i.href));
	});

	// Check if the current page is one of the secondary items in the drawer
	const isSecondaryActive = $derived(secondaryItems.some((it) => isActive(it.href)));

	// Combined badge count for secondary items
	const secondaryBadgeCount = $derived(
		secondaryItems.reduce((acc, it) => acc + (it.badge ?? 0), 0)
	);

	function openDrawer() {
		drawerOpen = true;
		if (typeof document !== 'undefined') {
			document.body.style.overflow = 'hidden';
			const main = document.querySelector('.portal-main') as HTMLElement | null;
			if (main) main.inert = true;
		}
		setTimeout(() => {
			drawerSheetEl?.focus();
		}, 60);
	}

	function closeDrawer() {
		drawerOpen = false;
		if (typeof document !== 'undefined') {
			document.body.style.overflow = '';
			const main = document.querySelector('.portal-main') as HTMLElement | null;
			if (main) main.inert = false;
		}
	}

	function toggleDrawer() {
		if (drawerOpen) closeDrawer();
		else openDrawer();
	}

	function onKeydown(e: KeyboardEvent) {
		if (drawerOpen && e.key === 'Escape') {
			e.preventDefault();
			closeDrawer();
		}
	}

	// Auto-close drawer ONLY when an actual route navigation occurs
	let lastPath = page.url.pathname;
	$effect(() => {
		const newPath = page.url.pathname;
		if (newPath !== lastPath) {
			lastPath = newPath;
			if (drawerOpen) closeDrawer();
		}
	});

	async function logout(e: Event) {
		e.preventDefault();
		if (drawerOpen) closeDrawer();
		await post(fetch, '/auth/logout').catch(() => {});
		goto('/login', { invalidateAll: true });
	}
</script>

<svelte:window onkeydown={onKeydown} />

<!-- Desktop Sidebar Rail (Hidden on screens <= 760px) -->
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

<!-- Mobile Bottom Navigation Bar (Important Menus Only + Burger Button) -->
<nav class="mobile-bottom-bar" aria-label="Mobile quick navigation">
	<ul class="mobile-bottom-list">
		{#each primaryItems as it (it.href)}
			<li>
				<a
					href={it.href}
					class="mobile-bottom-item"
					class:on={isActive(it.href)}
					aria-current={isActive(it.href) ? 'page' : undefined}
					title={it.label}
				>
					<div class="icon-wrap">
						<Icon name={it.icon} size={19} />
						{#if it.badge}
							<span class="badge mini">{it.badge > 99 ? '99+' : it.badge}</span>
						{/if}
					</div>
					<span class="lbl">{it.label}</span>
				</a>
			</li>
		{/each}

		<!-- Burger Button to trigger Side Drawer for full menu -->
		<li>
			<button
				type="button"
				bind:this={burgerBtnEl}
				class="mobile-bottom-item burger-trigger-btn"
				class:on={drawerOpen || isSecondaryActive}
				onclick={toggleDrawer}
				aria-label="Open full menu"
				aria-expanded={drawerOpen}
				aria-controls="mobile-nav-drawer"
			>
				<div class="icon-wrap">
					<Icon name="menu" size={20} />
					{#if secondaryBadgeCount > 0}
						<span class="badge mini">{secondaryBadgeCount > 99 ? '99+' : secondaryBadgeCount}</span>
					{/if}
				</div>
				<span class="lbl">Menu</span>
			</button>
		</li>
	</ul>
</nav>

<!-- Burger Side Drawer for Full Menu -->
<div
	class="mobile-drawer-root"
	class:open={drawerOpen}
	id="mobile-nav-drawer"
	aria-hidden={!drawerOpen}
>
	<!-- Dimmed backdrop overlay with light-dismiss -->
	<div
		class="drawer-backdrop"
		onclick={closeDrawer}
		role="presentation"
		aria-hidden="true"
	></div>

	<!-- Sliding sheet panel -->
	<aside
		class="drawer-panel"
		bind:this={drawerSheetEl}
		tabindex="-1"
		aria-label="Full navigation menu"
	>
		<!-- Animated leaves background in header -->
		<div class="drawer-leaves"><LeafField count={10} /></div>

		<!-- Drawer Header -->
		<div class="drawer-header">
			<a href="/" class="drawer-brand" onclick={closeDrawer}>
				<span class="logo"><Sprig size={18} /></span>
				<span class="brand-text">Functional Health</span>
			</a>
			<button
				type="button"
				class="drawer-close-btn"
				onclick={closeDrawer}
				aria-label="Close menu"
			>
				<Icon name="x" size={18} />
			</button>
		</div>

		<!-- User Identity Card -->
		<div class="drawer-user">
			<span class="avatar" aria-hidden="true">{initials}</span>
			<div class="user-info">
				<span class="user-name" title={userLabel}>{userLabel ?? 'User'}</span>
				<span class="user-role">{switcherTo === 'admin' ? 'Practitioner' : 'Admin'}</span>
			</div>
		</div>

		<!-- Quick Search Trigger -->
		{#if onCommandPalette}
			<button
				type="button"
				class="drawer-search-btn"
				onclick={() => { closeDrawer(); onCommandPalette(); }}
				aria-label="Search (⌘K)"
			>
				<Icon name="search" size={15} />
				<span class="lbl">Search everything…</span>
				<kbd>⌘K</kbd>
			</button>
		{/if}

		<!-- Full Navigation Menu List -->
		<div class="drawer-nav-section">
			<span class="drawer-section-title">Navigation</span>
			<ul class="drawer-list">
				{#each items as it (it.href)}
					<li>
						<a
							href={it.href}
							class="drawer-item"
							class:on={isActive(it.href)}
							onclick={async (e) => {
								e.preventDefault();
								closeDrawer();
								try {
									await goto(it.href);
								} catch (err) {
									console.error("Navigation error:", err);
								}
							}}
							aria-current={isActive(it.href) ? 'page' : undefined}
							title={it.locked ? `${it.label} (Pro)` : it.label}
						>
							<Icon name={it.icon} size={18} />
							<span class="lbl">{it.label}</span>
							{#if it.locked}<span class="pro">Pro</span>{/if}
							{#if it.badge}<span class="badge">{it.badge > 99 ? '99+' : it.badge}</span>{/if}
						</a>
					</li>
				{/each}
			</ul>
		</div>

		<!-- Drawer Footer Actions -->
		<div class="drawer-footer">
			{#if showSwitcher}
				<a
					class="drawer-footer-btn"
					href={switcherTo === 'admin' ? '/admin' : '/practitioner'}
					onclick={closeDrawer}
				>
					<Icon name="switch" size={17} />
					<span class="lbl">{switcherTo === 'admin' ? 'Switch to Admin view' : 'Switch to Practitioner view'}</span>
				</a>
			{/if}

			<form method="post" action="/api/auth/logout" onsubmit={logout} class="drawer-logout-form">
				<button type="submit" class="drawer-footer-btn logout-btn" title="Sign out" aria-label="Sign out">
					<Icon name="power" size={17} />
					<span class="lbl">Sign out</span>
				</button>
			</form>
		</div>
	</aside>
</div>

<style>
	/* ── DESKTOP SIDEBAR RAIL ────────────────────────────────────────── */
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
		display: inline-flex; align-items: center; justify-content: center;
		background: none; border: none; box-shadow: none; color: var(--rail-indicator);
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

	/* ── MOBILE HIDDEN BY DEFAULT ON DESKTOP ─────────────────────────── */
	.mobile-bottom-bar,
	.mobile-drawer-root {
		display: none;
	}

	/* ── MOBILE RESPONSIVE LAYOUT (<= 760px) ─────────────────────────── */
	@media (max-width: 760px) {
		/* Completely hide the vertical sidebar on mobile */
		.rail {
			display: none !important;
		}

		/* ── Mobile Bottom Navigation Bar ── */
		.mobile-bottom-bar {
			display: block;
			position: fixed;
			bottom: 0;
			left: 0;
			right: 0;
			height: calc(3.65rem + env(safe-area-inset-bottom, 0));
			padding-bottom: env(safe-area-inset-bottom, 0);
			background: color-mix(in srgb, var(--rail-bg) 96%, transparent);
			backdrop-filter: blur(20px) saturate(160%);
			-webkit-backdrop-filter: blur(20px) saturate(160%);
			border-top: 1px solid rgba(255, 255, 255, .12);
			z-index: 50;
			box-shadow: 0 -4px 20px rgba(0, 0, 0, .3);
		}
		.mobile-bottom-list {
			display: grid;
			grid-template-columns: repeat(4, 1fr);
			height: 3.65rem;
			margin: 0;
			padding: 0;
			list-style: none;
		}
		.mobile-bottom-item {
			display: flex;
			flex-direction: column;
			align-items: center;
			justify-content: center;
			gap: .2rem;
			height: 100%;
			width: 100%;
			border: none;
			background: transparent;
			color: rgba(230, 233, 240, .65);
			text-decoration: none;
			cursor: pointer;
			position: relative;
			padding: 0;
			transition: color var(--duration-fast);
		}
		.mobile-bottom-item:hover,
		.mobile-bottom-item:focus-visible {
			color: #fff;
		}
		.mobile-bottom-item.on {
			color: #fff;
		}
		.mobile-bottom-item.on::before {
			content: '';
			position: absolute;
			top: 0;
			left: 20%;
			right: 20%;
			height: 3px;
			border-radius: 0 0 3px 3px;
			background: var(--rail-indicator);
		}
		.mobile-bottom-item.on :global(svg) {
			color: var(--rail-indicator);
		}
		.mobile-bottom-item .lbl {
			flex: none;
			font-size: .64rem;
			font-weight: 600;
			letter-spacing: -.01em;
			line-height: 1;
		}
		.icon-wrap {
			position: relative;
			display: flex;
			align-items: center;
			justify-content: center;
		}
		.badge.mini {
			position: absolute;
			top: -5px;
			right: -9px;
			min-width: .95rem;
			height: .95rem;
			font-size: .55rem;
			line-height: .95rem;
			padding: 0 .22rem;
		}

		/* ── Burger Side Drawer Root ── */
		.mobile-drawer-root {
			display: block;
			position: fixed;
			inset: 0;
			pointer-events: none;
			visibility: hidden;
			z-index: 90;
		}
		.mobile-drawer-root.open {
			pointer-events: auto;
			visibility: visible;
		}

		/* Dimmed Backdrop Overlay */
		.drawer-backdrop {
			position: fixed;
			inset: 0;
			background: rgba(0, 0, 0, .65);
			backdrop-filter: blur(5px);
			-webkit-backdrop-filter: blur(5px);
			z-index: 99;
			opacity: 0;
			pointer-events: none;
			transition: opacity .25s ease;
		}
		.mobile-drawer-root.open .drawer-backdrop {
			opacity: 1;
			pointer-events: auto;
		}

		/* Sliding Drawer Sheet Panel */
		.drawer-panel {
			position: fixed;
			top: 0;
			bottom: 0;
			left: 0;
			width: min(21rem, 84dvw);
			height: 100svh;
			background:
				radial-gradient(120% 60% at 0% 0%, color-mix(in srgb, var(--rail-indicator) 22%, transparent), transparent 60%),
				var(--rail-bg);
			color: var(--rail-ink);
			z-index: 100;
			display: flex;
			flex-direction: column;
			overflow-y: auto;
			overscroll-behavior: contain;
			transform: translateX(-100%);
			transition: transform .28s cubic-bezier(.16, 1, .3, 1);
			box-shadow: 14px 0 40px rgba(0, 0, 0, .5);
			border-right: 1px solid rgba(255, 255, 255, .1);
			isolation: isolate;
			padding-bottom: env(safe-area-inset-bottom, 0);
		}
		.mobile-drawer-root.open .drawer-panel {
			transform: translateX(0);
		}

		.drawer-leaves {
			position: absolute;
			inset: 0;
			z-index: 0;
			--leaf-color: var(--rail-indicator);
			filter: brightness(1.7) saturate(1.2);
			pointer-events: none;
		}
		.drawer-panel > :not(.drawer-leaves) {
			position: relative;
			z-index: 1;
		}

		/* Drawer Header */
		.drawer-header {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: var(--space-4) var(--space-4) var(--space-3);
			border-bottom: 1px solid rgba(255, 255, 255, .08);
		}
		.drawer-brand {
			display: flex;
			align-items: center;
			gap: .65rem;
			color: #fff;
			text-decoration: none;
		}
		.brand-text {
			font-weight: 650;
			font-size: var(--text-base);
			letter-spacing: -.01em;
		}
		.drawer-close-btn {
			display: grid;
			place-items: center;
			width: 2.25rem;
			height: 2.25rem;
			border-radius: 9px;
			border: 1px solid rgba(255, 255, 255, .12);
			background: rgba(255, 255, 255, .06);
			color: rgba(230, 233, 240, .85);
			cursor: pointer;
			transition: background .15s ease, color .15s ease;
		}
		.drawer-close-btn:hover {
			background: rgba(255, 255, 255, .12);
			color: #fff;
		}

		/* User Profile Row */
		.drawer-user {
			display: flex;
			align-items: center;
			gap: .75rem;
			padding: .65rem .75rem;
			margin: var(--space-3) var(--space-3) 0;
			border-radius: 12px;
			background: rgba(255, 255, 255, .05);
			border: 1px solid rgba(255, 255, 255, .08);
		}
		.drawer-user .avatar {
			flex: 0 0 auto;
			width: 2.3rem;
			height: 2.3rem;
			border-radius: 50%;
			display: grid;
			place-items: center;
			background: color-mix(in srgb, var(--rail-indicator) 28%, transparent);
			color: #fff;
			font-size: .8rem;
			font-weight: 700;
		}
		.user-info {
			display: flex;
			flex-direction: column;
			min-width: 0;
			flex: 1;
		}
		.user-name {
			font-size: var(--text-sm);
			font-weight: 600;
			color: #fff;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
		}
		.user-role {
			font-size: .7rem;
			color: rgba(230, 233, 240, .6);
			text-transform: capitalize;
		}

		/* Search trigger in Drawer */
		.drawer-search-btn {
			display: flex;
			align-items: center;
			gap: .55rem;
			margin: var(--space-3) var(--space-3) 0;
			height: 2.45rem;
			padding: 0 .75rem;
			border: 1px solid rgba(255, 255, 255, .1);
			border-radius: var(--r);
			background: rgba(255, 255, 255, .05);
			color: rgba(230, 233, 240, .7);
			cursor: pointer;
			font: inherit;
			text-align: left;
			transition: background var(--duration-fast), color var(--duration-fast);
		}
		.drawer-search-btn:hover {
			background: rgba(255, 255, 255, .09);
			color: #fff;
		}
		.drawer-search-btn .lbl {
			flex: 1;
			font-size: var(--text-sm);
		}
		.drawer-search-btn kbd {
			font: inherit;
			font-size: .68rem;
			padding: .05rem .35rem;
			border-radius: 5px;
			background: rgba(255, 255, 255, .08);
			color: rgba(230, 233, 240, .65);
		}

		/* Navigation Menu List */
		.drawer-nav-section {
			display: flex;
			flex-direction: column;
			gap: var(--space-2);
			padding: var(--space-4) var(--space-3);
			flex: 1 1 auto;
		}
		.drawer-section-title {
			font-size: .68rem;
			font-weight: 650;
			text-transform: uppercase;
			letter-spacing: .08em;
			color: rgba(230, 233, 240, .45);
			padding: 0 .5rem;
		}
		.drawer-list {
			list-style: none;
			margin: 0;
			padding: 0;
			display: flex;
			flex-direction: column;
			gap: 3px;
		}
		.drawer-item {
			display: flex;
			align-items: center;
			gap: .75rem;
			width: 100%;
			height: 2.7rem;
			padding: 0 .75rem;
			color: rgba(230, 233, 240, .75);
			text-decoration: none;
			position: relative;
			border-radius: var(--r);
			font-size: var(--text-sm);
			font-weight: 500;
			transition: background var(--duration-fast), color var(--duration-fast);
		}
		.drawer-item:hover {
			background: rgba(255, 255, 255, .06);
			color: #fff;
		}
		.drawer-item.on {
			background: linear-gradient(90deg, color-mix(in srgb, var(--rail-indicator) 24%, transparent), rgba(255, 255, 255, .06));
			color: #fff;
			box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .08);
			font-weight: 600;
		}
		.drawer-item.on::before {
			content: '';
			position: absolute;
			left: -.4rem;
			top: .45rem;
			bottom: .45rem;
			width: 3.5px;
			border-radius: 0 3px 3px 0;
			background: var(--rail-indicator);
		}
		.drawer-item.on :global(svg) {
			color: var(--rail-indicator);
		}

		/* Footer Actions */
		.drawer-footer {
			margin-top: auto;
			display: flex;
			flex-direction: column;
			gap: var(--space-2);
			padding: var(--space-3);
			border-top: 1px solid rgba(255, 255, 255, .08);
			background: rgba(0, 0, 0, .15);
		}
		.drawer-footer-btn {
			display: flex;
			align-items: center;
			gap: .75rem;
			width: 100%;
			height: 2.5rem;
			padding: 0 .75rem;
			border-radius: var(--r);
			color: rgba(230, 233, 240, .75);
			text-decoration: none;
			border: none;
			background: transparent;
			cursor: pointer;
			font: inherit;
			font-size: var(--text-sm);
			font-weight: 500;
			transition: background var(--duration-fast), color var(--duration-fast);
		}
		.drawer-footer-btn:hover {
			background: rgba(255, 255, 255, .08);
			color: #fff;
		}
		.drawer-logout-form {
			margin: 0;
			width: 100%;
		}
		.logout-btn {
			color: #ff8fa3;
		}
		.logout-btn:hover {
			background: rgba(255, 143, 163, .12);
			color: #ff8fa3;
		}
	}
</style>
