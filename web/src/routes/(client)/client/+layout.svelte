<script lang="ts">
	import { page } from '$app/state';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import DisclaimerBar from '$lib/components/DisclaimerBar.svelte';
	import Icon from '$lib/components/Icon.svelte';

	// specs/v8 §8.5 — surfaced on the two client-facing record pages the
	// spec names specifically, not every page in the portal.
	const showDisclaimer = $derived(['/client/questionnaire', '/client/record'].some((p) => page.url.pathname.startsWith(p)));

	let { data, children } = $props();

	// Direct instruction: no persistent nav surface — "Your care" (this
	// portal's own root +page.svelte) is the one place a client starts
	// from and returns to.
	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
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
<button class="search-trigger" onclick={() => (paletteOpen = true)} aria-label="Search (⌘K)" title="Search (⌘K)">
	<Icon name="search" size={17} />
</button>
<AccountMenu userLabel={data.session?.name} />

<main class="container">
	{@render children()}
	{#if showDisclaimer}<DisclaimerBar />{/if}
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
