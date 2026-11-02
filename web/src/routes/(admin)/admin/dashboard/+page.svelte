<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import StatTile from '$lib/components/StatTile.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Toggle from '$lib/components/Toggle.svelte';

	let { data } = $props();
	const s = $derived(data.stats ?? {});
	const health = $derived(data.health);
	const isSuperadmin = $derived(data.session?.admin_role === 'superadmin');
	let switchingProvider = $state(false);
	// Optimistic-ish: reflects the last load's value, then whatever the
	// toggle just set — invalidateAll() below re-syncs it from the server.
	let llmProvider = $state(data.llmProvider);
	$effect(() => { llmProvider = data.llmProvider; });

	// Role.EMBEDDER always stays on Nebius regardless of this setting —
	// Anthropic has no embeddings endpoint (app/clients/llm_client.py) —
	// so the toggle only covers the other five chat-model roles.
	async function setProvider(useAnthropic: boolean) {
		const provider = useAnthropic ? 'anthropic' : 'nebius';
		switchingProvider = true;
		try {
			await post(fetch, '/superadmin/llm-provider', { provider });
			llmProvider = provider;
			toast(`AI team switched to ${provider === 'anthropic' ? 'Anthropic (Opus/Sonnet/Haiku)' : 'Nebius'}.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			switchingProvider = false;
		}
	}
	// Fields site_stats() (app/core_store.py) doesn't have a dedicated tile
	// for below — rendered generically so a future stat added there doesn't
	// need a matching frontend change to show up somewhere.
	const KNOWN_STATS = new Set([
		'total_views', 'total_contacts', 'new_contacts',
		'pending_practitioners', 'approved_practitioners',
	]);
	const otherStats = $derived(Object.entries(s).filter(([k]) => !KNOWN_STATS.has(k)));

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
	<StatTile
		label="Pending applications"
		value={s.pending_practitioners ?? 0}
		icon="clipboard"
		href="/admin/users"
	/>
	<StatTile
		label="Approved practitioners"
		value={s.approved_practitioners ?? 0}
		icon="users"
		href="/admin/users"
	/>
	<StatTile
		label="New contact submissions"
		value={s.new_contacts ?? 0}
		icon="mail"
		href="/admin/users"
	/>
	<StatTile
		label="Total profile views"
		value={s.total_views ?? 0}
		icon="eye"
	/>
	{#each otherStats as [key, value] (key)}
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

{#if isSuperadmin}
	<h2 class="section-title">AI model provider</h2>
	<p class="hint">
		Switches Reader, Graph-builder, Answer-engine, Reasoner and Checker-LLM between
		Nebius and Anthropic (Opus 5 / Sonnet 5 / Haiku 4.5). Embedder always stays on
		Nebius — Anthropic has no embeddings endpoint.
	</p>
	<div class="check-row provider-row">
		<Toggle
			checked={llmProvider === 'anthropic'}
			onchange={setProvider}
			disabled={switchingProvider}
			label="Use Anthropic for the AI team's chat roles"
		/>
		<span class="hint">{llmProvider === 'anthropic' ? 'Anthropic' : 'Nebius'}</span>
	</div>
{/if}

<style>
	.tiles { margin-top: var(--space-5); }
	.section-title { margin-top: var(--space-6); margin-bottom: var(--space-2); }
	.checks { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-3); }
	.check-row { display: flex; align-items: center; gap: .5rem; }
	.provider-row { margin-top: var(--space-3); }
</style>
