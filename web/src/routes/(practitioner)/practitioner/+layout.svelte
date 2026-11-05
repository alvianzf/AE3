<script lang="ts">
	import { useAppSurface } from '$lib/surface.svelte';
	import { page } from '$app/state';
	import Rail from '$lib/components/Rail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import DisclaimerBar from '$lib/components/DisclaimerBar.svelte';
	import { get } from '$lib/api';

	let { data, children } = $props();
	useAppSurface('practitioner');
	// specs/v8 §8.5 — surfaced specifically on Consult, the page a
	// practitioner actually forms a clinical judgment from.
	const showDisclaimer = $derived(page.url.pathname.startsWith('/practitioner/consult'));

	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: '.search-trigger', title: 'Search everything', body: 'Press ⌘K (or Ctrl+K) anytime to jump straight to a client or a past consult.' },
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
	// Omni-search: Cmd/Ctrl+K also reaches a practitioner's own clients,
	// not just the nav — fetched once, lazily, on first open.
	let searchExtra = $state<{ label: string; href: string; icon?: string; group?: string }[]>([]);
	let omniLoaded = false;
	async function loadOmniIndex() {
		if (omniLoaded || !isPro) return;
		omniLoaded = true;
		const clients = await get(fetch, '/me/clients').catch(() => []);
		searchExtra = (clients ?? []).map((c: any) => ({
			label: c.name, href: `/practitioner/clients/${c.id}`, icon: 'users', group: 'Clients'
		}));
	}

	const paletteItems = $derived([...items.map((i) => ({ ...i, group: i.locked ? 'Pro' : 'Practitioner' })), ...searchExtra]);
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
	<Rail {items} onCommandPalette={openPalette} userLabel={data.profile?.name} />
	{@render children()}
</div>
{#if showDisclaimer}<DisclaimerBar />{/if}

