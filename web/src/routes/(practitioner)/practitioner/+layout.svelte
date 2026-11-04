<script lang="ts">
	import { page } from '$app/state';
	import AppRail from '$lib/components/AppRail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';

	let { data, children } = $props();

	// specs/v7/06 — same rail-only scoping as the admin portal's tour;
	// see that layout's own comment for why.
	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: 'a[href="/practitioner/dashboard"]', title: 'Dashboard', body: 'Your at-a-glance view — new contacts, unread client intake, and more.' },
		{ selector: 'a[href="/practitioner/consult"]', title: 'Consult', body: 'Ask grounded, cited questions about a client — this is where you’ll spend most of your time.' },
		{ selector: 'a[href="/practitioner/clients"]', title: 'Clients', body: 'Review and manage each client’s record — conditions, medications, and notes.' },
		{ selector: '.search-trigger', title: 'Jump anywhere', body: 'Press ⌘K (or Ctrl+K) from any page to jump straight to any section.' }
	];

	// Consult/Clients/Knowledge 403 for a Basic-plan practitioner
	// (require_pro_practitioner) — previously that was only discoverable by
	// clicking in and hitting the error toast (specs/v4/04-known-issues.md#m15).
	const isPro = $derived(data.profile?.plan === 'pro');

	const items = $derived([
		{ href: '/practitioner/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/practitioner/clients', label: 'Clients', icon: 'users', locked: !isPro, badge: data.notifications?.unviewed_intake },
		{ href: '/practitioner/consult', label: 'Consult', icon: 'message', locked: !isPro },
		{ href: '/practitioner/contacts', label: 'Contacts', icon: 'mail', badge: data.notifications?.new_contacts },
		{ href: '/practitioner/knowledge', label: 'Library weights', icon: 'book', locked: !isPro },
		{ href: '/practitioner/questionnaires', label: 'Questionnaires', icon: 'clipboard', locked: !isPro },
		{ href: '/practitioner/profile', label: 'Profile', icon: 'settings' },
		{ href: '/practitioner/upgrade', label: 'Upgrade', icon: 'star' }
	]);

	// specs/v7/06 — same group label convention as locked items' own
	// title tooltip in AppRail ("label (Pro)") so a palette result makes
	// the same promise the rail icon it's standing in for already does.
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

<div class="shell">
	<AppRail {items} portalLabel="Practitioner portal" userLabel={data.profile?.name} onCommandPalette={() => (paletteOpen = true)} />
	<main>
		{@render children()}
	</main>
</div>

<style>
	.shell {
		display: flex; align-items: flex-start; min-height: 100dvh;
		/* specs/v4.1/02 — practitioner portal's own rail identity, via the
		   same CSS custom properties AppRail already reads (a cascade
		   override, not component-side role logic). */
		--rail-top: rgba(20, 108, 104, .88);
		--rail-bottom: rgba(6, 40, 38, .94);
		--rail-indicator: #7fe0d6;
	}
	main { flex: 1 1 auto; min-width: 0; padding: var(--space-6) var(--space-5); }
</style>
