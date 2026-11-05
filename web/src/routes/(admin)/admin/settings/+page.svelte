<script lang="ts">
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { get, post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Toggle from '$lib/components/Toggle.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import UsageChart from '$lib/components/UsageChart.svelte';

	let { data } = $props();
	// Mirrors the backend's own guard (POST /api/superadmin/llm-provider
	// is require_superadmin) — a plain admin can still reach this route
	// (the parent layout only checks role==='admin'), so the toggle
	// itself must stay hidden for them too, not just silently 403 on click.
	const isSuperadmin = $derived(data.session?.admin_role === 'superadmin');
	let switchingProvider = $state(false);
	let llmProvider = $state(data.llmProvider);
	$effect(() => { llmProvider = data.llmProvider; });

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

	// Polled, not just loaded once — this page is exactly where an admin
	// would leave a tab open to watch the box during a bulk ingest or a
	// traffic spike. Same interval the backend samples at
	// (_USAGE_SAMPLE_INTERVAL_S, 60s) — polling faster than that would
	// just repeat the same point.
	let usage = $state(data.usage);
	onMount(() => {
		const timer = setInterval(async () => {
			usage = await get(fetch, '/admin/system-usage').catch(() => usage);
		}, 60_000);
		return () => clearInterval(timer);
	});

	function toPoints(key: string): { x: number; y: number }[] {
		return (usage?.samples ?? [])
			.filter((s: any) => s[key] !== undefined)
			.map((s: any) => ({ x: s.ts, y: s[key] }));
	}
	const loadPoints = $derived(toPoints('load1'));
	const memPoints = $derived(toPoints('mem_used_mb'));
	const memTotalMb = $derived(usage?.samples?.at(-1)?.mem_total_mb);
</script>

<svelte:head><title>Settings — Admin portal</title></svelte:head>

<div class="pane-row">
<div class="detail-pane">
<div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="settings" size={16} /></span><h1>Settings</h1></div></div>

	<section class="block">
		<div class="block-head">
			<span class="block-ico"><Icon name="bolt" size={16} /></span>
			<h2>System health</h2>
			<Chip tone={health?.status === 'ok' ? 'ok' : 'danger'}>{health?.status ?? 'unknown'}</Chip>
		</div>
		<div class="check-grid">
			{#each checks as c (c.label)}
				<div class="check-tile">
					<span class="check-label">{c.label}</span>
					<Chip tone={c.ok ? 'ok' : 'danger'}>{c.ok ? `${c.ping}ms` : 'down'}</Chip>
				</div>
			{/each}
		</div>
	</section>

	<section class="block">
		<div class="block-head">
			<span class="block-ico"><Icon name="bolt" size={16} /></span>
			<h2>Usage &amp; load</h2>
			<Chip tone="neutral">last 3h</Chip>
		</div>
		{#if usage?.samples?.length}
			<div class="usage-grid">
				<div>
					<span class="check-label">Load average (1 min)</span>
					<UsageChart points={loadPoints} />
				</div>
				<div>
					<span class="check-label">Memory used{memTotalMb ? ` of ${(memTotalMb / 1024).toFixed(1)}GB` : ''}</span>
					<UsageChart points={memPoints} unit="MB" color="var(--accent-ink)" />
				</div>
			</div>
		{:else}
			<p class="hint">No usage history yet — this server only samples load/memory on Linux (production), not local dev, and the trend fills in over the next few minutes after a restart.</p>
		{/if}
	</section>

	{#if isSuperadmin}
		<section class="block">
			<div class="block-head">
				<span class="block-ico"><Icon name="settings" size={16} /></span>
				<h2>AI model provider</h2>
				<Chip tone="accent">{llmProvider === 'anthropic' ? 'Anthropic' : 'Nebius'}</Chip>
			</div>
			<p class="hint">
				Switches Reader, Graph-builder, Answer-engine, Reasoner and Checker-LLM between
				Nebius and Anthropic (Opus 5 / Sonnet 5 / Haiku 4.5). This toggle never touches
				Embedder — Anthropic has no embeddings endpoint — but that doesn't mean Embedder
				is on Nebius either; check System health below for what it's actually running
				(a local CPU fallback kicks in independently, e.g. during a Nebius billing gap).
			</p>
			<Toggle
				checked={llmProvider === 'anthropic'}
				onchange={setProvider}
				disabled={switchingProvider}
				label="Use Anthropic for the AI team's chat roles"
			/>
		</section>
	{/if}
</div>
</div>

<style>
	.block {
		margin-bottom: var(--space-5); padding: var(--space-4) var(--space-5);
		border: 1px solid var(--glass-border); border-radius: var(--r-lg); background: var(--panel-2);
	}
	.block-head { display: flex; align-items: center; gap: .5rem; margin-bottom: var(--space-3); }
	.block-ico {
		display: flex; align-items: center; justify-content: center; flex: 0 0 auto;
		width: 1.8rem; height: 1.8rem; border-radius: 50%; background: var(--accent-soft); color: var(--accent-ink);
	}
	.block-head h2 { font-size: var(--text-base); font-weight: var(--weight-bold); flex: 1 1 auto; }
	.check-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr)); gap: .5rem; }
	.check-tile {
		display: flex; align-items: center; justify-content: space-between; gap: .5rem;
		padding: .5rem .7rem; border: 1px solid var(--line); border-radius: var(--r); background: var(--panel);
	}
	.check-label { font-size: var(--text-sm); color: var(--ink-2); text-transform: capitalize; }
	.usage-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: var(--space-5); }
	.usage-grid .check-label { display: block; margin-bottom: .4rem; }
</style>
