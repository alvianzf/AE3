<script lang="ts">
	import AppRail from '$lib/components/AppRail.svelte';

	let { data, children } = $props();

	const items = [
		{ href: '/client/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/client/questionnaire', label: 'Questionnaire', icon: 'clipboard' },
		{ href: '/client/record', label: 'Health record', icon: 'user-card' },
		{ href: '/client/files', label: 'Files', icon: 'folder' },
		{ href: '/client/wearables', label: 'Wearables', icon: 'watch' }
	];
</script>

<div class="shell">
	<!-- No role-specific rail colors needed here — the global --rail-top/
	     --rail-bottom/--rail-indicator defaults (app.css) already are the
	     client portal's identity; practitioner and admin override them on
	     their own .shell instead. -->
	<AppRail {items} portalLabel="Client portal" userLabel={data.session?.name} />
	<main>
		{@render children()}
	</main>
</div>

<style>
	.shell { display: flex; align-items: flex-start; min-height: 100dvh; }
	main { flex: 1 1 auto; min-width: 0; padding: var(--space-6) var(--space-5); }
</style>
