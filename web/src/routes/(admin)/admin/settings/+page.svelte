<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Toggle from '$lib/components/Toggle.svelte';

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
</script>

<svelte:head><title>Settings — Admin portal</title></svelte:head>

<div class="pane-row">
<div class="detail-pane">
<div class="detail-head"><div><h1>Settings</h1></div></div>
	<section class="block">
		<h2>System health</h2>
		<p class:ok={health?.status === 'ok'} class="overall">{health?.status ?? 'unknown'}</p>
		<ul class="checks">
			{#each checks as c (c.label)}
				<li><span class="dot" class:ok={c.ok}></span>{c.label} — {c.ok ? `${c.ping}ms` : 'down'}</li>
			{/each}
		</ul>
	</section>

	{#if isSuperadmin}
		<section class="block">
			<h2>AI model provider</h2>
			<p class="hint">
				Switches Reader, Graph-builder, Answer-engine, Reasoner and Checker-LLM between
				Nebius and Anthropic (Opus 5 / Sonnet 5 / Haiku 4.5). Embedder always stays on
				Nebius — Anthropic has no embeddings endpoint.
			</p>
			<div class="check-row">
				<Toggle
					checked={llmProvider === 'anthropic'}
					onchange={setProvider}
					disabled={switchingProvider}
					label="Use Anthropic for the AI team's chat roles"
				/>
				<span class="hint">{llmProvider === 'anthropic' ? 'Anthropic' : 'Nebius'}</span>
			</div>
		</section>
	{/if}
</div>
</div>

<style>
	.block { margin-bottom: var(--space-6); }
	.block h2 { font-size: var(--text-lg); margin-bottom: var(--space-2); }
	.overall { font-weight: 650; text-transform: uppercase; color: var(--danger); margin-bottom: var(--space-3); }
	.overall.ok { color: var(--ok); }
	.checks { list-style: none; margin: 0; padding: 0; display: grid; gap: .4rem; font-size: var(--text-sm); color: var(--ink-2); }
	.checks li { display: flex; align-items: center; gap: .5rem; }
	.dot { width: .5rem; height: .5rem; border-radius: 50%; background: var(--danger); }
	.dot.ok { background: var(--ok); }
	.check-row { display: flex; align-items: center; gap: .5rem; margin-top: var(--space-2); }
</style>
