<script lang="ts">
	import AppRail from '$lib/components/AppRail.svelte';

	let { children } = $props();

	const items = [
		{ href: '/admin', label: 'Knowledge', icon: 'book' },
		{ href: '/admin/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/admin/users', label: 'Users', icon: 'users' },
		{ href: '/admin/questionnaires', label: 'Questionnaires', icon: 'clipboard' },
		{ href: '/admin/audit', label: 'Audit history', icon: 'history' }
	];
</script>

<div class="shell">
	<AppRail {items} portalLabel="Admin portal" />
	<main>
		{@render children()}
	</main>
</div>

<style>
	.shell { display: flex; align-items: flex-start; min-height: 100dvh; }
	/* No .container max-width here on purpose: admin screens are data-dense
	   (tables, a directory grid) and benefit from the full width next to the
	   icon-only AppRail, unlike the public site's prose-width pages that
	   .container is tuned for — a fixed 78rem cap left wide empty gutters on
	   anything wider than a laptop. */
	main { flex: 1 1 auto; min-width: 0; padding: var(--space-6) var(--space-5); }
</style>
