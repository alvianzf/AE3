<script lang="ts">
	import { page } from '$app/state';
	import Rail from '$lib/components/Rail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';
	import DisclaimerBar from '$lib/components/DisclaimerBar.svelte';
	import AskLibraryModal from '$lib/components/AskLibraryModal.svelte';
	import { askLibrary } from '$lib/stores/askLibrary.svelte';
	import { get } from '$lib/api';
	import { PRO_FEATURES } from '$lib/proFeatures';

	let { data, children } = $props();
	// specs/v8 §8.5 — surfaced specifically on Consult, the page a
	// practitioner actually forms a clinical judgment from.
	const showDisclaimer = $derived(page.url.pathname.startsWith('/practitioner/consult'));

	let tourActive = $state(!data.session?.tour_completed);
	const isPro = $derived(data.profile?.plan === 'pro');
	// A Basic practitioner's tour used to point at Consult and Clients —
	// both locked for them — and never mentioned Upgrade at all
	// (ux-implementation-spec.md#3).
	const PRO_TOUR_STEPS = [
		{ selector: '.search-trigger', title: 'Search everything', body: 'Press ⌘K (or Ctrl+K) anytime to jump straight to a client or a past consult.' },
		{ selector: 'a[href="/practitioner/consult"]', title: 'Consult', body: 'Ask grounded, cited questions about a client — this is where you’ll spend most of your time.' },
		{ selector: 'a[href="/practitioner/clients"]', title: 'Clients', body: 'Review and manage each client’s record — conditions, medications, and notes.' }
	];
	const BASIC_TOUR_STEPS = [
		{ selector: '.search-trigger', title: 'Search everything', body: 'Press ⌘K (or Ctrl+K) anytime to jump straight to a client or a past consult.' },
		{ selector: 'a[href="/practitioner/profile"]', title: 'Complete your profile', body: 'This is the one thing worth doing first — it\'s what clients and other practitioners see.' },
		{ selector: 'a[href="/practitioner/upgrade"]', title: 'Upgrade when you\'re ready', body: 'Consult, Clients, Library weights, and Intake all unlock on Pro.' }
	];
	const tourSteps = $derived(isPro ? PRO_TOUR_STEPS : BASIC_TOUR_STEPS);
	const PRO_HREFS = new Set(PRO_FEATURES.map((f) => f.href));
	const items = $derived([
		{ href: '/practitioner', label: 'Home', icon: 'home', primary: true },
		{ href: '/practitioner/consult', label: 'Consult', icon: 'message', primary: true },
		{ href: '/practitioner/clients', label: 'Clients', icon: 'users', primary: true },
		{ href: '/practitioner/contacts', label: 'Contacts', icon: 'mail' },
		{ href: '/practitioner/knowledge', label: 'Library weights', icon: 'book' },
		{ href: '/practitioner/questionnaires', label: 'Intake', icon: 'clipboard' },
		{ href: '/practitioner/profile', label: 'Profile', icon: 'settings' },
		// A Basic practitioner's dashboard CTA pointed at Upgrade but this
		// page was never in the nav, so navigating anywhere else meant
		// first finding the URL by hand (journey-audit finding #9).
		...(isPro ? [] : [{ href: '/practitioner/upgrade', label: 'Upgrade', icon: 'star' }])
	].map((it) => ({ ...it, locked: PRO_HREFS.has(it.href) && !isPro })));
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

<div class="app-shell portal portal-practitioner">
	<Rail {items} onCommandPalette={openPalette} onAskLibrary={isPro ? () => askLibrary.open() : undefined}
		userLabel={data.profile?.name} showSwitcher={data.session?.role === 'admin'} switcherTo="admin" />
	<main class="portal-main">
		{@render children()}
	</main>
</div>
{#if showDisclaimer}<DisclaimerBar />{/if}
<!-- Mounted once here, not per-page — reachable from the Rail's global
     button on every practitioner page, and from the dashboard's own
     compact preview card; both drive the same shared askLibrary store
     (web/src/lib/stores/askLibrary.svelte.ts), so the conversation is
     identical regardless of where it was opened from. Pro-gated same as
     the backend route (auth.require_pro_practitioner). -->
{#if isPro}<AskLibraryModal />{/if}

