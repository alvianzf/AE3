<script lang="ts">
	import AppRail from '$lib/components/AppRail.svelte';

	let { data, children } = $props();

	const items = [
		{ href: '/practitioner/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/practitioner/clients', label: 'Clients', icon: 'users' },
		{ href: '/practitioner/consult', label: 'Consult', icon: 'message' },
		{ href: '/practitioner/contacts', label: 'Contacts', icon: 'mail' },
		{ href: '/practitioner/knowledge', label: 'Knowledge', icon: 'book' },
		{ href: '/practitioner/profile', label: 'Profile', icon: 'settings' },
		{ href: '/practitioner/upgrade', label: 'Upgrade', icon: 'star' }
	];
</script>

<div class="shell">
	<AppRail {items} portalLabel="Practitioner portal" userLabel={data.profile?.name} />
	<main class="container">
		{@render children()}
	</main>
</div>

<style>
	.shell { display: flex; align-items: flex-start; min-height: 100dvh; }
	main { flex: 1 1 auto; padding: var(--space-6) var(--space-5); }
</style>
