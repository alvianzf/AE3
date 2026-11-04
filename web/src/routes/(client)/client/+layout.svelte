<script lang="ts">
	import AppRail from '$lib/components/AppRail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';

	let { data, children } = $props();

	const items = [
		{ href: '/client/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/client/questionnaire', label: 'Questionnaire', icon: 'clipboard' },
		{ href: '/client/record', label: 'Health record', icon: 'user-card' },
		{ href: '/client/files', label: 'Files', icon: 'folder' },
		{ href: '/client/wearables', label: 'Wearables', icon: 'watch' }
	];

	// specs/v7/06 — included for consistency across all three portals even
	// though a 5-item rail barely needs a search palette on its own
	// (specs/v7/05's own stated lower priority here) — same component,
	// same shortcut everywhere a user might look for it.
	const paletteItems = items.map((i) => ({ ...i, group: 'Client' }));
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

<div class="shell">
	<!-- No role-specific rail colors needed here — the global --rail-top/
	     --rail-bottom/--rail-indicator defaults (app.css) already are the
	     client portal's identity; practitioner and admin override them on
	     their own .shell instead. -->
	<AppRail {items} portalLabel="Client portal" userLabel={data.session?.name} onCommandPalette={() => (paletteOpen = true)} />
	<main>
		{@render children()}
	</main>
</div>

<style>
	.shell { display: flex; align-items: flex-start; min-height: 100dvh; }
	main { flex: 1 1 auto; min-width: 0; padding: var(--space-6) var(--space-5); }
</style>
