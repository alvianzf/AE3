<script lang="ts">
	import { page } from '$app/state';
	import AccountMenu from '$lib/components/AccountMenu.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import DisclaimerBar from '$lib/components/DisclaimerBar.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data, children } = $props();
	// specs/v8 §8.5 — surfaced specifically on Consult, the page a
	// practitioner actually forms a clinical judgment from.
	const showDisclaimer = $derived(page.url.pathname.startsWith('/practitioner/consult'));

	// Direct instruction: no persistent nav surface — the Home launcher
	// (this portal's own root +page.svelte) is how a practitioner gets
	// anywhere now, not an always-present rail.
	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: 'a[href="/practitioner/consult"]', title: 'Consult', body: 'Ask grounded, cited questions about a client — this is where you’ll spend most of your time.' },
		{ selector: 'a[href="/practitioner/clients"]', title: 'Clients', body: 'Review and manage each client’s record — conditions, medications, and notes.' }
	];

	const isPro = $derived(data.profile?.plan === 'pro');
	const items = $derived([
		{ href: '/practitioner', label: 'Home', icon: 'home' },
		{ href: '/practitioner/consult', label: 'Consult', icon: 'message', locked: !isPro },
		{ href: '/practitioner/clients', label: 'Clients', icon: 'users', locked: !isPro },
		{ href: '/practitioner/contacts', label: 'Contacts', icon: 'mail' },
		{ href: '/practitioner/knowledge', label: 'Library weights', icon: 'book', locked: !isPro },
		{ href: '/practitioner/questionnaires', label: 'Questionnaires', icon: 'clipboard', locked: !isPro },
		{ href: '/practitioner/profile', label: 'Profile', icon: 'settings' }
	]);
	const paletteItems = $derived(items.map((i) => ({ ...i, group: i.locked ? 'Pro' : 'Practitioner' })));
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
<AccountMenu userLabel={data.profile?.name} />

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
