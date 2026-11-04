<script lang="ts">
	import AppRail from '$lib/components/AppRail.svelte';
	import CommandPalette from '$lib/components/CommandPalette.svelte';

	let { data, children } = $props();

	const items = [
		{ href: '/admin/dashboard', label: 'Dashboard', icon: 'home' },
		{ href: '/admin', label: 'Library', icon: 'book' },
		{ href: '/admin/users', label: 'Users', icon: 'users' },
		{ href: '/admin/questionnaires', label: 'Questionnaires', icon: 'clipboard' },
		{ href: '/admin/audit', label: 'Audit history', icon: 'history' }
	];

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

<div class="shell">
	<AppRail {items} portalLabel="Admin portal" userLabel={data.session?.admin_role} onCommandPalette={() => (paletteOpen = true)} />
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

<style>
	.shell {
		display: flex; align-items: flex-start; min-height: 100dvh;
		/* specs/v4.1/02 — admin portal's own rail identity, via the same
		   CSS custom properties AppRail already reads. */
		--rail-top: rgba(70, 60, 90, .9);
		--rail-bottom: rgba(20, 16, 30, .95);
		--rail-indicator: #c9b8ff;
	}
	/* No .container max-width here on purpose: admin screens are data-dense
	   (tables, a directory grid) and benefit from the full width next to the
	   icon-only AppRail, unlike the public site's prose-width pages that
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
