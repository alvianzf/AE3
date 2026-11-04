<script lang="ts">
	import { page } from '$app/state';
	import AppRail from '$lib/components/AppRail.svelte';
	import TopBar from '$lib/components/TopBar.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import DisclaimerBar from '$lib/components/DisclaimerBar.svelte';

	// specs/v8 §8.5 — surfaced on the two client-facing record pages the
	// spec names specifically, not every page in the portal.
	const showDisclaimer = $derived(['/client/questionnaire', '/client/record'].some((p) => page.url.pathname.startsWith(p)));

	let { data, children } = $props();

	// specs/v7/05 — onboarding matters most on this portal of the three
	// (a client didn't choose this software, their practitioner did) —
	// warmer copy than the other two portals' tours, and the Health
	// record step folds in the trust/privacy note specs/v7/06 called
	// out explicitly, since there's no separate page to put it on at
	// this (rail-only, see specs/v7/06's admin-layout comment for why)
	// scope.
	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: 'a[href="/client/dashboard"]', title: 'Welcome', body: 'Start here each time you log in — a quick look at what’s new.' },
		{ selector: 'a[href="/client/questionnaire"]', title: 'Questionnaire', body: 'Your practitioner uses this to understand your health history.' },
		{ selector: 'a[href="/client/record"]', title: 'Health record', body: 'Only you and your practitioner can see what’s here — never shared beyond your own care.' },
		{ selector: 'a[href="/client/files"]', title: 'Files', body: 'Documents your practitioner has shared with you, in one place.' }
	];

	const items = [
		{ href: '/client/dashboard', label: 'Dashboard', icon: 'home', navGroup: 'primary' as const },
		{ href: '/client/questionnaire', label: 'Questionnaire', icon: 'clipboard' },
		{ href: '/client/record', label: 'Health record', icon: 'user-card' },
		{ href: '/client/files', label: 'Files', icon: 'folder' },
		{ href: '/client/wearables', label: 'Wearables', icon: 'watch' }
	];

	const crumb = $derived(items.find((i) => page.url.pathname === i.href || page.url.pathname.startsWith(i.href + '/'))?.label ?? 'Client portal');

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
<Tour steps={tourSteps} bind:active={tourActive} />

<div class="shell">
	<!-- No role-specific rail colors needed here — the global --rail-top/
	     --rail-bottom/--rail-indicator defaults (app.css) already are the
	     client portal's identity; practitioner and admin override them on
	     their own .shell instead. -->
	<AppRail {items} portalLabel="Client portal" />
	<div class="col">
		<TopBar
			crumbs={[{ label: 'Client portal' }, { label: crumb }]}
			onCommandPalette={() => (paletteOpen = true)}
			userLabel={data.session?.name}
		/>
		<main>
			{@render children()}
			{#if showDisclaimer}<DisclaimerBar />{/if}
		</main>
	</div>
</div>

<style>
	.shell { display: flex; align-items: flex-start; min-height: 100dvh; }
	.col { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; min-height: 100dvh; }
	main { flex: 1 1 auto; min-width: 0; padding: var(--space-6) var(--space-5); }
</style>
