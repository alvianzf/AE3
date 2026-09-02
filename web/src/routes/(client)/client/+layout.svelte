<script lang="ts">
	import AppRail from '$lib/components/AppRail.svelte';

	let { children } = $props();

	const items = [
		{ href: '/client/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/client/questionnaire', label: 'Questionnaire', icon: 'clipboard' },
		{ href: '/client/files', label: 'Files', icon: 'folder' },
		{ href: '/client/wearables', label: 'Wearables', icon: 'watch' }
	];
</script>

<div class="shell">
	<AppRail {items} portalLabel="Client portal" />
	<main class="container">
		{@render children()}
	</main>
</div>

<style>
	.shell { display: flex; align-items: flex-start; min-height: 100dvh; }
	main { flex: 1 1 auto; padding: var(--space-6) var(--space-5); }
</style>
