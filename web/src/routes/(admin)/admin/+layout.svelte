<script lang="ts">
	import Rail from '$lib/components/Rail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import { get } from '$lib/api';

	let { data, children } = $props();

	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: 'a[href="/admin/library"]', title: 'Library', body: 'Upload, organize, and browse the knowledge base — folders, tags, and a live graph view of how it all connects.' },
		{ selector: 'a[href="/admin/users"]', title: 'Users', body: 'Review practitioner applications, and manage admin and client accounts.' }
	];

	const items = [
		{ href: '/admin', label: 'Overview', icon: 'home' },
		{ href: '/admin/library', label: 'Library', icon: 'book' },
		{ href: '/admin/users', label: 'Users', icon: 'users' },
		{ href: '/admin/questionnaires', label: 'Questionnaires', icon: 'clipboard' },
		{ href: '/admin/audit', label: 'Audit history', icon: 'history' },
		{ href: '/admin/settings', label: 'Settings', icon: 'settings' }
	];
	// Omni-search (direct instruction): Cmd/Ctrl+K should reach more than
	// just the nav — documents, practitioners, clients too. Fetched once,
	// lazily, on first open (not on every portal page load) since none of
	// these lists are otherwise needed just to render the shell.
	let searchExtra = $state<{ label: string; href: string; icon?: string; group?: string }[]>([]);
	let omniLoaded = false;
	async function loadOmniIndex() {
		if (omniLoaded) return;
		omniLoaded = true;
		const [sources, practitioners, clients] = await Promise.all([
			get(fetch, '/sources').catch(() => []),
			get(fetch, '/admin/practitioners').catch(() => []),
			get(fetch, '/admin/clients').catch(() => [])
		]);
		searchExtra = [
			...(sources ?? []).map((s: any) => ({ label: s.title, href: `/admin/${s.id}`, icon: 'file', group: 'Documents' })),
			...(practitioners ?? []).map((p: any) => ({
				label: p.name, icon: 'users', group: 'Practitioners',
				href: `/admin/users?tab=practitioners&q=${encodeURIComponent(p.name ?? '')}`
			})),
			...(clients ?? []).map((c: any) => ({
				label: c.name, icon: 'user-card', group: 'Clients',
				href: `/admin/users?tab=clients&q=${encodeURIComponent(c.name ?? '')}`
			}))
		];
	}

	const paletteItems = $derived([...items.map((i) => ({ ...i, group: 'Admin' })), ...searchExtra]);
	let paletteOpen = $state(false);

	function openPalette() {
		paletteOpen = true;
		loadOmniIndex();
	}

	function onWindowKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			openPalette();
		}
	}
</script>

<svelte:window onkeydown={onWindowKeydown} />

<CommandPalette items={paletteItems} bind:open={paletteOpen} />
<Tour steps={tourSteps} bind:active={tourActive} />

<div class="app-shell">
	<Rail
		{items}
		onCommandPalette={openPalette}
		userLabel={data.session?.name ?? data.session?.admin_role}
		showSwitcher={!!data.session?.has_practitioner_view}
		switcherTo="practitioner"
	/>
	{@render children()}
</div>

<style>
	.app-shell { --rail-indicator: #c9b8ff; }
</style>
