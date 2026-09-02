<script lang="ts">
	import AppRail from '$lib/components/AppRail.svelte';

	let { children } = $props();

	const items = [
		{ href: '/admin', label: 'Knowledge', icon: 'book' },
		{ href: '/admin/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/admin/users', label: 'Users', icon: 'users' },
		{ href: '/admin/questionnaires', label: 'Questionnaires', icon: 'clipboard' }
	];
</script>

<div class="shell">
	<AppRail {items} portalLabel="Admin portal" />
	<main class="container">
		{@render children()}
	</main>
</div>

<style>
	.shell { display: flex; align-items: flex-start; min-height: 100dvh; }
	main { flex: 1 1 auto; padding: var(--space-6) var(--space-5); }
</style>
