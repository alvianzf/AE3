<script lang="ts">
	import { page } from '$app/state';
	import Rail from '$lib/components/Rail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import DisclaimerBar from '$lib/components/DisclaimerBar.svelte';

	let { data, children } = $props();
	// specs/v8 §8.5 — surfaced specifically on Consult, the page a
	// practitioner actually forms a clinical judgment from.
	const showDisclaimer = $derived(page.url.pathname.startsWith('/practitioner/consult'));

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

<div class="app-shell">
	<Rail {items} onCommandPalette={() => (paletteOpen = true)} userLabel={data.profile?.name} />
	{@render children()}
</div>
{#if showDisclaimer}<DisclaimerBar />{/if}

<style>
	.app-shell { --rail-indicator: #7fe0d6; }
</style>
