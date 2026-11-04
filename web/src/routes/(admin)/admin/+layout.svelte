<script lang="ts">
	import Rail from '$lib/components/Rail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';

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

<div class="app-shell">
	<Rail
		{items}
		onCommandPalette={() => (paletteOpen = true)}
		userLabel={data.session?.admin_role}
		showSwitcher={!!data.session?.has_practitioner_view}
		switcherTo="practitioner"
	/>
	{@render children()}
</div>

<style>
	.app-shell { --rail-indicator: #c9b8ff; }
</style>
