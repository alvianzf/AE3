<script lang="ts">
	import { page } from '$app/state';
	import AppRail from '$lib/components/AppRail.svelte';

	let { data, children } = $props();

	// Consult/Clients/Knowledge 403 for a Basic-plan practitioner
	// (require_pro_practitioner) — previously that was only discoverable by
	// clicking in and hitting the error toast (specs/v4/04-known-issues.md#m15).
	const isPro = $derived(data.profile?.plan === 'pro');

	// The consult page is a chat app, not a prose-width form/list page like
	// the rest of this portal — .container's 78rem cap (app.css, tuned for
	// the public site's prose pages) left it with wide empty gutters on
	// anything wider than a laptop, found live. Same opt-out the admin
	// Library page already makes for the same reason (see that layout's
	// own comment) — scoped to just this one route rather than removing
	// the cap portal-wide, since Dashboard/Clients/Profile are exactly the
	// narrower list/form pages .container is meant for.
	const isFullWidth = $derived(page.url.pathname.startsWith('/practitioner/consult'));
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
	<main class:container={!isFullWidth}>
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
