<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();
	const s = $derived(data.stats ?? {});
	const health = $derived(data.health);

	// GET /api/health already reports neo4j/postgres + per-role AI-team
	// status (reader/graph_builder/embedder/reasoner/checker) — nothing
	// under /admin surfaced it before, so an outage was only visible by
	// curling the endpoint directly. Flattened into one list of chips:
	// simple ok/degraded visibility, not a full dashboard.
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
</script>

<svelte:head><title>Dashboard — Admin portal</title></svelte:head>

<h1>Site stats</h1>
<p class="hint">A quick read on the whole platform.</p>

<div class="grid-auto tiles">
	{#each Object.entries(s) as [key, value] (key)}
		<StatTile label={key.replaceAll('_', ' ')} value={String(value)} />
	{/each}
</div>

<h2 class="section-title">System health</h2>
{#if health}
	<p class="hint">Overall: <Chip tone={health.status === 'ok' ? 'ok' : 'warn'}>{health.status}</Chip></p>
	<div class="checks">
		{#each checks as c (c.label)}
			<div class="check-row">
				<Chip tone={c.ok ? 'ok' : 'danger'}>{c.label}</Chip>
				<span class="hint">{c.ok ? `${c.ping}ms` : 'down'}</span>
			</div>
		{/each}
	</div>
{:else}
	<p class="hint">Health check unavailable.</p>
{/if}

<style>
	.tiles { margin-top: var(--space-5); }
	.section-title { margin-top: var(--space-6); margin-bottom: var(--space-2); }
	.checks { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }
	.check-row { display: flex; align-items: center; gap: .5rem; }
</style>
