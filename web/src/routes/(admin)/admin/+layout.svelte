<script lang="ts">
	import Rail from '$lib/components/Rail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import { get } from '$lib/api';

	let { data, children } = $props();

	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: '.search-trigger', title: 'Search everything', body: 'Press ⌘K (or Ctrl+K) anytime to jump straight to a document, practitioner, client, folder, or questionnaire.' },
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
		// per_page=500, same as the Library's own load — the bare
		// GET /sources default (per_page=10) was silently limiting
		// document search to the 10 newest.
		const [sourcesRes, practitioners, clients, questionnaires] = await Promise.all([
			get(fetch, '/sources?per_page=500').catch(() => ({ sources: [] })),
			get(fetch, '/admin/practitioners').catch(() => []),
			get(fetch, '/admin/clients').catch(() => []),
			get(fetch, '/admin/questionnaires').catch(() => [])
		]);
		const sources = sourcesRes?.sources ?? sourcesRes ?? [];
		const folderPaths = [...new Set(
			(sources ?? []).map((s: any) => s.folder_path).filter((p: string) => p)
		)] as string[];
		searchExtra = [
			...folderPaths.map((p) => ({
				label: p.split('/').pop() ?? p, icon: 'folder', group: 'Folders',
				href: `/admin/library?folder=${encodeURIComponent(p)}`
			})),
			...(sources ?? []).map((s: any) => ({ label: s.title, href: `/admin/${s.id}`, icon: 'file', group: 'Documents' })),
			...(practitioners ?? []).map((p: any) => ({
				label: p.name, icon: 'users', group: 'Practitioners',
				href: `/admin/users?tab=practitioners&q=${encodeURIComponent(p.name ?? '')}`
			})),
			...(clients ?? []).map((c: any) => ({
				label: c.name, icon: 'user-card', group: 'Clients',
				href: `/admin/users?tab=clients&q=${encodeURIComponent(c.name ?? '')}`
			})),
			...(questionnaires ?? []).map((q: any) => ({
				label: q.title, icon: 'clipboard', group: 'Questionnaires', href: `/admin/questionnaires`
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

<div class="app-shell portal portal-admin">
	<Rail
		{items}
		onCommandPalette={openPalette}
		userLabel={data.session?.name ?? data.session?.admin_role}
		showSwitcher={!!data.session?.has_practitioner_view}
		switcherTo="practitioner"
	/>
	<main class="portal-main">
		{@render children()}
	</main>
</div>

