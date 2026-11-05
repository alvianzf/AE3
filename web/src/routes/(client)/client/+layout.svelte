<script lang="ts">
	import { page } from '$app/state';
	import Rail from '$lib/components/Rail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import DisclaimerBar from '$lib/components/DisclaimerBar.svelte';

	// specs/v8 §8.5 — surfaced on the two client-facing record pages the
	// spec names specifically, not every page in the portal.
	const showDisclaimer = $derived(['/client/questionnaire', '/client/record'].some((p) => page.url.pathname.startsWith(p)));

	let { data, children } = $props();

	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: '.search-trigger', title: 'Jump to a page', body: 'Press ⌘K (or Ctrl+K) anytime to jump straight to any page in your portal.' },
		{ selector: 'a[href="/client/questionnaire"]', title: 'Questionnaire', body: 'Your practitioner uses this to understand your health history.' },
		{ selector: 'a[href="/client/record"]', title: 'Health record', body: 'Only you and your practitioner can see what’s here — never shared beyond your own care.' }
	];

	const items = [
		{ href: '/client', label: 'Home', icon: 'home' },
		{ href: '/client/questionnaire', label: 'Questionnaire', icon: 'clipboard' },
		{ href: '/client/record', label: 'Health record', icon: 'user-card' },
		{ href: '/client/files', label: 'Files', icon: 'folder' },
		{ href: '/client/wearables', label: 'Wearables', icon: 'watch' }
	];
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
<Tour steps={tourSteps} bind:active={tourActive} />

<div class="app-shell portal portal-client">
	<Rail {items} onCommandPalette={() => (paletteOpen = true)} userLabel={data.session?.name} />
	<main class="portal-main">
		{@render children()}
	</main>
</div>
{#if showDisclaimer}<DisclaimerBar />{/if}
