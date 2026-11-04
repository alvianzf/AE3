<script lang="ts">
	import { page } from '$app/state';
	import AppRail from '$lib/components/AppRail.svelte';
	import TopBar from '$lib/components/TopBar.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';
	import Tour from '$lib/components/Tour.svelte';

	let { data, children } = $props();

	// specs/v7/06 — mounted at the layout level, so step targets are
	// restricted to elements guaranteed present on every admin page
	// (the rail itself), not page-specific content like the Library
	// page's own "+ Add resources" button — that only exists while
	// actually on /admin, and a tour step whose target isn't on the
	// current page would have nothing to highlight.
	let tourActive = $state(!data.session?.tour_completed);
	const tourSteps = [
		{ selector: 'a[href="/admin/dashboard"]', title: 'Dashboard', body: 'A quick read on the whole platform — pending applications, new contacts, profile views.' },
		{ selector: 'a[href="/admin"]', title: 'Library', body: 'Upload, organize, and browse the knowledge base — folders, tags, and a live graph view of how it all connects.' },
		{ selector: '.search-trigger', title: 'Jump anywhere', body: 'Press ⌘K (or Ctrl+K) from any page to jump straight to Library, Users, Questionnaires, or Audit history.' },
		{ selector: 'a[href="/admin/users"]', title: 'Users', body: 'Review practitioner applications, and manage admin and client accounts.' }
	];

	// specs/v8 §7.1 — Library is the admin portal's actual job-to-be-done
	// (the most-used surface, per this session's own research), so it's
	// the primary nav group; everything else is secondary/account-shaped.
	const items = [
		{ href: '/admin', label: 'Library', icon: 'book', group: 'primary' as const },
		{ href: '/admin/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/admin/users', label: 'Users', icon: 'users' },
		{ href: '/admin/questionnaires', label: 'Questionnaires', icon: 'clipboard' },
		{ href: '/admin/audit', label: 'Audit history', icon: 'history' }
	];

	const crumb = $derived(items.find((i) => page.url.pathname === i.href || page.url.pathname.startsWith(i.href + '/'))?.label ?? 'Admin portal');

	// specs/v7/06 — v1 scope is navigation only; the Library page's own
	// view modes/tabs (Tree view, Graph view) aren't separate routes to
	// jump to yet, so they're not command-palette entries here. Adding a
	// query-param-addressable deep link for those is a reasonable later
	// follow-up, not attempted in this first pass.
	const paletteItems = items.map((i) => ({ ...i, group: 'Admin' }));
	let paletteOpen = $state(false);

	function onWindowKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			paletteOpen = true;
		}
	}

	// A slim, persistent status bar on every admin page — replaces the
	// dashboard-only "System health" block of per-role chips with just a
	// dot per check; hover (title) for the ms/error detail a chip used to
	// spell out.
	const health = $derived(data.health);
	const checks = $derived.by(() => {
		if (!health) return [];
		const rows = [
			{ label: 'Neo4j', ok: health.checks?.neo4j?.ok, ping: health.checks?.neo4j?.ping_ms },
			{ label: 'Postgres', ok: health.checks?.postgres?.ok, ping: health.checks?.postgres?.ping_ms }
		];
		for (const [role, r] of Object.entries(health.checks?.ai_team?.roles ?? {})) {
			rows.push({ label: role.replaceAll('_', ' '), ok: (r as any).ok, ping: (r as any).ping_ms });
		}
		return rows;
	});
	function title(c: any) {
		return `${c.label}: ${c.ok ? `${c.ping}ms` : 'down'}`;
	}
</script>

<svelte:window onkeydown={onWindowKeydown} />

<CommandPalette items={paletteItems} bind:open={paletteOpen} />
<Tour steps={tourSteps} bind:active={tourActive} />

<div class="shell">
	<AppRail {items} portalLabel="Admin portal" />
	<div class="col">
		<TopBar
			crumbs={[{ label: 'Admin portal' }, { label: crumb }]}
			onCommandPalette={() => (paletteOpen = true)}
			userLabel={data.session?.admin_role}
			showSwitcher={!!data.session?.has_practitioner_view}
			switcherTo="practitioner"
		/>
		<main>
		{@render children()}
		{#if health}
			<footer class="health-bar">
				<span class="overall" class:ok={health.status === 'ok'}>{health.status}</span>
				{#each checks as c (c.label)}
					<span class="dot" class:ok={c.ok} title={title(c)}></span>
				{/each}
			</footer>
		{/if}
		</main>
	</div>
</div>

<style>
	.shell {
		display: flex; align-items: flex-start; min-height: 100dvh;
		/* specs/v4.1/02 — admin portal's own rail identity, via the same
		   CSS custom properties AppRail already reads. */
		--rail-top: rgba(70, 60, 90, .9);
		--rail-bottom: rgba(20, 16, 30, .95);
		--rail-indicator: #c9b8ff;
	}
	.col { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; min-height: 100dvh; }
	/* No .container max-width here on purpose: admin screens are data-dense
	   (tables, a directory grid) and benefit from the full width next to the
	   label-visible AppRail, unlike the public site's prose-width pages that
	   .container is tuned for — a fixed 78rem cap left wide empty gutters on
	   anything wider than a laptop. */
	main { flex: 1 1 auto; min-width: 0; padding: var(--space-6) var(--space-5); }
	.health-bar {
		position: sticky; bottom: 0; margin: var(--space-6) calc(var(--space-5) * -1) calc(var(--space-6) * -1);
		display: flex; align-items: center; gap: .4rem; padding: .4rem var(--space-5);
		background: var(--panel); border-top: 1px solid var(--line); font-size: var(--text-xs);
	}
	.overall {
		font-weight: 650; text-transform: uppercase; letter-spacing: .03em; color: var(--danger);
	}
	.overall.ok { color: var(--ok); }
	.dot {
		width: .5rem; height: .5rem; border-radius: 50%; background: var(--danger); flex: 0 0 auto; cursor: default;
	}
	.dot.ok { background: var(--ok); }
</style>
