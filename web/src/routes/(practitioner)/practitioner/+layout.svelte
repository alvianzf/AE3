<script lang="ts">
	import AppRail from '$lib/components/AppRail.svelte';

	let { data, children } = $props();

	// Consult/Clients/Knowledge 403 for a Basic-plan practitioner
	// (require_pro_practitioner) — previously that was only discoverable by
	// clicking in and hitting the error toast (specs/v4/04-known-issues.md#m15).
	const isPro = $derived(data.profile?.plan === 'pro');
	const items = $derived([
		{ href: '/practitioner/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/practitioner/clients', label: 'Clients', icon: 'users', locked: !isPro },
		{ href: '/practitioner/consult', label: 'Consult', icon: 'message', locked: !isPro },
		{ href: '/practitioner/contacts', label: 'Contacts', icon: 'mail' },
		{ href: '/practitioner/knowledge', label: 'Library weights', icon: 'book', locked: !isPro },
		{ href: '/practitioner/profile', label: 'Profile', icon: 'settings' },
		{ href: '/practitioner/upgrade', label: 'Upgrade', icon: 'star' }
	]);
</script>

<div class="shell">
	<AppRail {items} portalLabel="Practitioner portal" userLabel={data.profile?.name} />
	<main class="container">
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
	main { flex: 1 1 auto; padding: var(--space-6) var(--space-5); }
</style>
