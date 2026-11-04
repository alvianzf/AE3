<script lang="ts">
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data, children } = $props();

	// Direct instruction: no persistent nav surface at all — see /admin's
	// own +page.svelte (the Home launcher) for how navigation actually
	// works now. The tour below targets the launcher tiles instead of a
	// rail, since that's the only thing guaranteed present on first login.
	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: 'a[href="/admin/library"]', title: 'Library', body: 'Upload, organize, and browse the knowledge base — folders, tags, and a live graph view of how it all connects.' },
		{ selector: 'a[href="/admin/users"]', title: 'Users', body: 'Review practitioner applications, and manage admin and client accounts.' }
	];

	const items = [
		{ href: '/admin', label: 'Home', icon: 'home' },
		{ href: '/admin/library', label: 'Library', icon: 'book' },
		{ href: '/admin/users', label: 'Users', icon: 'users' },
		{ href: '/admin/questionnaires', label: 'Questionnaires', icon: 'clipboard' },
		{ href: '/admin/audit', label: 'Audit history', icon: 'history' }
	];
	const paletteItems = items.map((i) => ({ ...i, group: 'Admin' }));
	let paletteOpen = $state(false);

	function onWindowKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			paletteOpen = true;
		}
	}
</script>

<svelte:window onkeydown={onWindowKeydown} />

<CommandPalette items={paletteItems} bind:open={paletteOpen} />
<Tour steps={tourSteps} bind:active={tourActive} />
<button class="search-trigger" onclick={() => (paletteOpen = true)} aria-label="Search (⌘K)" title="Search (⌘K)">
	<Icon name="search" size={17} />
</button>
<AccountMenu
	userLabel={data.session?.admin_role}
	showSwitcher={!!data.session?.has_practitioner_view}
	switcherTo="practitioner"
/>

<main class="container">
	{@render children()}
</main>

<style>
	main { padding: var(--space-6) var(--space-5) var(--space-7); min-height: 100dvh; }
	.search-trigger {
		position: fixed; top: var(--space-4); right: 4.2rem; z-index: 50;
		width: 2.4rem; height: 2.4rem; border-radius: 50%; background: var(--panel);
		border: 1px solid var(--line); box-shadow: var(--shadow); color: var(--ink-2); cursor: pointer;
		display: flex; align-items: center; justify-content: center;
	}
	.search-trigger:hover { background: var(--panel-2); }
</style>
