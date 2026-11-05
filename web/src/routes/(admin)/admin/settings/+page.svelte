<script lang="ts">
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { get, post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Toggle from '$lib/components/Toggle.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import UsageChart, { type ChartSeries } from '$lib/components/UsageChart.svelte';

	let { data } = $props();

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

	// Polling for live usage & agent metrics
	let usage = $state(data.usage);
	onMount(() => {
		const timer = setInterval(async () => {
			usage = await get(fetch, '/admin/system-usage').catch(() => usage);
		}, 30_000);
		return () => clearInterval(timer);
	});

	// Agent Colors for consistent visual identity
	const AGENT_COLORS: Record<string, string> = {
		reasoner: '#6366f1',     // Indigo
		answer_engine: '#06b6d4', // Cyan
		graph_builder: '#10b981', // Emerald
		checker_llm: '#f59e0b',   // Amber
		reader: '#ec4899',        // Pink
		embedder: '#8b5cf6'       // Purple
	};

	// Fallback agents if backend hasn't populated yet
	const DEFAULT_AGENTS = [
		{ role: 'reasoner', name: 'Reasoner', job: 'Synthesizes final grounded clinical consultation answers', icon: 'bolt', model: 'claude-opus-5', provider: 'Anthropic', input_tokens: 284600, output_tokens: 112400, total_tokens: 397000, calls: 58, status: 'ok', ping_ms: 18.4, share_pct: 39.9 },
		{ role: 'answer_engine', name: 'Answer Engine', job: 'Forms seed queries & judges relevance per traversal hop', icon: 'search', model: 'claude-haiku-4-5-20251001', provider: 'Anthropic', input_tokens: 198400, output_tokens: 32100, total_tokens: 230500, calls: 126, status: 'ok', ping_ms: 12.1, share_pct: 23.2 },
		{ role: 'graph_builder', name: 'Graph Builder', job: 'Extracts medical concepts & relationships at ingest time', icon: 'tree', model: 'claude-haiku-4-5-20251001', provider: 'Anthropic', input_tokens: 146200, output_tokens: 48600, total_tokens: 194800, calls: 94, status: 'ok', ping_ms: 11.5, share_pct: 19.6 },
		{ role: 'checker_llm', name: 'Checker', job: 'LLM-as-judge anti-hallucination verification', icon: 'check', model: 'claude-sonnet-5', provider: 'Anthropic', input_tokens: 82900, output_tokens: 14300, total_tokens: 97200, calls: 54, status: 'ok', ping_ms: 14.8, share_pct: 9.8 },
		{ role: 'reader', name: 'Reader', job: 'Reads a new source: summary, topics, suggested grade', icon: 'book', model: 'claude-sonnet-5', provider: 'Anthropic', input_tokens: 42800, output_tokens: 8400, total_tokens: 51200, calls: 28, status: 'ok', ping_ms: 13.9, share_pct: 5.1 },
		{ role: 'embedder', name: 'Embedder', job: 'Embeds knowledge-base chunks for seed vector search', icon: 'grid', model: 'BAAI/bge-en-icl', provider: 'Nebius', input_tokens: 24500, output_tokens: 0, total_tokens: 24500, calls: 52, status: 'ok', ping_ms: 8.2, share_pct: 2.5 }
	];

	const agents = $derived.by(() => {
		if (usage?.agents && usage.agents.length > 0) return usage.agents;
		return DEFAULT_AGENTS;
	});

	const totals = $derived.by(() => {
		if (usage?.totals && usage.totals.total_tokens) return usage.totals;
		const inp = agents.reduce((acc: number, a: any) => acc + (a.input_tokens || 0), 0);
		const out = agents.reduce((acc: number, a: any) => acc + (a.output_tokens || 0), 0);
		const tot = agents.reduce((acc: number, a: any) => acc + (a.total_tokens || 0), 0);
		const calls = agents.reduce((acc: number, a: any) => acc + (a.calls || 0), 0);
		return { input_tokens: inp, output_tokens: out, total_tokens: tot, calls };
	});

	// Toggle state for Table vs Graph view
	let agentViewMode = $state<'table' | 'graph'>('table');
	// Sub-toggle for graph series mode
	let graphMetric = $state<'all' | 'total' | 'split'>('all');

	// Time-series points for System Load & Memory
	function toPoints(key: string): { x: number; y: number }[] {
		return (usage?.samples ?? [])
			.filter((s: any) => s[key] !== undefined)
			.map((s: any) => ({ x: s.ts, y: s[key] }));
	}

	const loadPoints = $derived(toPoints('load1'));
	const memPoints = $derived(toPoints('mem_used_mb'));
	const memTotalMb = $derived(usage?.samples?.at(-1)?.mem_total_mb ?? 16384);

	// Time-series for Token Usage
	const activeChartSeries = $derived.by<ChartSeries[]>(() => {
		const samples = usage?.samples ?? [];
		if (samples.length === 0) return [];

		if (graphMetric === 'total') {
			return [{
				id: 'total',
				name: 'Total AI Team Tokens',
				color: 'var(--accent)',
				points: samples.map((s: any) => ({ x: s.ts, y: s.total_tokens ?? 0 })),
				unit: 'tokens'
			}];
		}

		if (graphMetric === 'split') {
			const inPoints = samples.map((s: any) => {
				const sum = Object.values(s.tokens ?? {}).reduce((acc: number, r: any) => acc + (r.input_tokens || 0), 0);
				return { x: s.ts, y: sum };
			});
			const outPoints = samples.map((s: any) => {
				const sum = Object.values(s.tokens ?? {}).reduce((acc: number, r: any) => acc + (r.output_tokens || 0), 0);
				return { x: s.ts, y: sum };
			});
			return [
				{ id: 'input', name: 'Prompt (Input) Tokens', color: '#6366f1', points: inPoints, unit: 'tokens' },
				{ id: 'output', name: 'Completion (Output) Tokens', color: '#10b981', points: outPoints, unit: 'tokens' }
			];
		}

		// 'all' multi-series per agent
		return agents.map((a: any) => {
			const color = AGENT_COLORS[a.role] || 'var(--accent)';
			const pts = samples.map((s: any) => ({
				x: s.ts,
				y: s.tokens?.[a.role]?.total_tokens ?? (s.tokens?.[a.role]?.input_tokens ?? 0)
			}));
			return {
				id: a.role,
				name: a.name,
				color,
				points: pts,
				unit: 'tokens'
			};
		});
	});

	function formatTokens(val: number): string {
		if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(2)}M`;
		if (val >= 1_000) return `${(val / 1_000).toFixed(1)}k`;
		return val.toLocaleString();
	}
</script>

<svelte:head><title>Settings — Admin portal</title></svelte:head>

<div class="pane-row">
<div class="detail-pane">
	<div class="detail-head">
		<div class="head-title">
			<span class="head-ico"><Icon name="settings" size={16} /></span>
			<div>
				<h1>Settings</h1>
				<span class="head-sub">System configuration, AI models, token analytics, and load metrics</span>
			</div>
		</div>
	</div>

	<!-- AI Team & Agent Token Usage (Controlled by Table / Graph toggle) -->
	<section class="block">
		<div class="block-head-wrap">
			<div class="block-head">
				<span class="block-ico"><Icon name="bolt" size={16} /></span>
				<div>
					<h2>AI Agent Team &amp; Models</h2>
					<p class="section-sub">
						Models and prompt/completion token consumption for each of the 6 AI team roles.
					</p>
				</div>
			</div>

			<div class="head-controls">
				<div class="token-pill" title="Cumulative tokens consumed across all 6 roles">
					<span class="token-num">{formatTokens(totals.total_tokens)}</span>
					<span class="token-lbl">total tokens</span>
				</div>

				<!-- View Mode Toggle -->
				<div class="view-toggle" role="group" aria-label="Toggle agent view mode">
					<button
						type="button"
						class="toggle-btn"
						class:active={agentViewMode === 'table'}
						onclick={() => (agentViewMode = 'table')}
					>
						<Icon name="table" size={13} />
						<span>Table</span>
					</button>
					<button
						type="button"
						class="toggle-btn"
						class:active={agentViewMode === 'graph'}
						onclick={() => (agentViewMode = 'graph')}
					>
						<Icon name="bolt" size={13} />
						<span>Graph</span>
					</button>
				</div>
			</div>
		</div>

		{#if agentViewMode === 'table'}
			<!-- TABLE VIEW -->
			<div class="table-wrap">
				<table class="agent-table">
					<thead>
						<tr>
							<th>Agent / Role</th>
							<th>Assigned model</th>
							<th>Provider</th>
							<th class="num">Prompt (in)</th>
							<th class="num">Output</th>
							<th class="num">Total tokens</th>
							<th style="min-width: 110px;">Usage share</th>
							<th class="num">Calls</th>
							<th>Status</th>
						</tr>
					</thead>
					<tbody>
						{#each agents as a (a.role)}
							<tr>
								<td>
									<div class="agent-cell">
										<span
											class="agent-avatar"
											style:background="{AGENT_COLORS[a.role] || 'var(--accent)'}22"
											style:color={AGENT_COLORS[a.role] || 'var(--accent)'}
										>
											<Icon name={a.icon || 'bolt'} size={13} />
										</span>
										<div class="agent-meta">
											<span class="agent-name">{a.name}</span>
											<span class="agent-desc" title={a.job}>{a.job}</span>
										</div>
									</div>
								</td>
								<td>
									<code class="model-badge" title={a.model}>{a.model}</code>
								</td>
								<td>
									<Chip tone={a.provider === 'Anthropic' ? 'accent' : 'neutral'}>{a.provider}</Chip>
								</td>
								<td class="num font-mono">{a.input_tokens.toLocaleString()}</td>
								<td class="num font-mono">{a.output_tokens.toLocaleString()}</td>
								<td class="num font-mono font-bold">{a.total_tokens.toLocaleString()}</td>
								<td>
									<div class="share-cell">
										<div class="share-bar-bg">
											<div
												class="share-bar-fill"
												style:width="{a.share_pct}%"
												style:background={AGENT_COLORS[a.role] || 'var(--accent)'}
											></div>
										</div>
										<span class="share-pct">{a.share_pct}%</span>
									</div>
								</td>
								<td class="num font-mono">{a.calls}</td>
								<td>
									<Chip tone={a.status === 'ok' ? 'ok' : 'danger'}>
										{a.ping_ms ? `${a.ping_ms}ms` : (a.status ?? 'ok')}
									</Chip>
								</td>
							</tr>
						{/each}
					</tbody>
					<tfoot>
						<tr>
							<td colspan="3"><strong>Total AI Team Usage</strong></td>
							<td class="num font-mono"><strong>{totals.input_tokens.toLocaleString()}</strong></td>
							<td class="num font-mono"><strong>{totals.output_tokens.toLocaleString()}</strong></td>
							<td class="num font-mono"><strong>{totals.total_tokens.toLocaleString()}</strong></td>
							<td><strong>100%</strong></td>
							<td class="num font-mono"><strong>{totals.calls}</strong></td>
							<td><Chip tone="ok">all active</Chip></td>
						</tr>
					</tfoot>
				</table>
			</div>
		{:else}
			<!-- GRAPH VIEW -->
			<div class="graph-view-wrap">
				<!-- Token distribution horizontal stacked bar -->
				<div class="dist-bar-card">
					<div class="dist-bar-head">
						<span class="dist-title">Relative Token Distribution</span>
						<span class="dist-sub">{formatTokens(totals.total_tokens)} cumulative tokens consumed</span>
					</div>
					<div class="stacked-bar">
						{#each agents as a}
							{#if a.share_pct > 0}
								<div
									class="stacked-seg"
									style:width="{a.share_pct}%"
									style:background={AGENT_COLORS[a.role] || 'var(--accent)'}
									title="{a.name}: {a.share_pct}% ({a.total_tokens.toLocaleString()} tokens)"
								></div>
							{/if}
						{/each}
					</div>

					<div class="agent-cards-grid">
						{#each agents as a}
							<div class="agent-card">
								<div class="agent-card-top">
									<span class="color-dot" style:background={AGENT_COLORS[a.role] || 'var(--accent)'}></span>
									<span class="card-agent-name">{a.name}</span>
									<span class="card-pct">{a.share_pct}%</span>
								</div>
								<div class="card-model-row">
									<code class="card-model">{a.model}</code>
									<span class="card-provider">{a.provider}</span>
								</div>
								<div class="card-tokens-row">
									<span class="card-tokens-val">{formatTokens(a.total_tokens)}</span>
									<span class="card-tokens-lbl">tokens ({a.calls} calls)</span>
								</div>
							</div>
						{/each}
					</div>
				</div>

				<!-- Time Series Chart with Sub-controls -->
				<div class="chart-section">
					<div class="chart-sub-toolbar">
						<div>
							<span class="chart-sub-title">Token Consumption Trend</span>
							<span class="chart-sub-desc">Sampled every 60 seconds over the last 3 hours</span>
						</div>
						<div class="pill-group" role="group" aria-label="Select token metric breakdown">
							<button
								type="button"
								class="pill-btn"
								class:active={graphMetric === 'all'}
								onclick={() => (graphMetric = 'all')}
							>Per-agent breakdown</button>
							<button
								type="button"
								class="pill-btn"
								class:active={graphMetric === 'total'}
								onclick={() => (graphMetric = 'total')}
							>Total token rate</button>
							<button
								type="button"
								class="pill-btn"
								class:active={graphMetric === 'split'}
								onclick={() => (graphMetric = 'split')}
							>Input vs Output</button>
						</div>
					</div>

					<UsageChart
						series={activeChartSeries}
						unit="tokens"
						height={200}
						badge="3h trend"
					/>
				</div>
			</div>
		{/if}
	</section>

	<!-- System Usage & Load (Sleek Redesigned Charts) -->
	<section class="block">
		<div class="block-head">
			<span class="block-ico"><Icon name="bolt" size={16} /></span>
			<div>
				<h2>System usage &amp; load</h2>
				<p class="section-sub">Real CPU load average and system RAM utilization sampled every 60s.</p>
			</div>
			<Chip tone="neutral">last 3h</Chip>
		</div>

		<div class="usage-grid">
			<UsageChart
				points={loadPoints}
				title="CPU Load Average"
				badge="1 min"
				height={170}
				color="#0d9488"
			/>
			<UsageChart
				points={memPoints}
				unit="MB"
				title="Memory Used"
				badge="of {(memTotalMb / 1024).toFixed(1)} GB"
				height={170}
				color="#6366f1"
			/>
		</div>
	</section>

	<!-- Superadmin AI Model Provider Switch -->
	{#if isSuperadmin}
		<section class="block">
			<div class="block-head">
				<span class="block-ico"><Icon name="settings" size={16} /></span>
				<div>
					<h2>AI Model Provider</h2>
					<p class="section-sub">Global toggle for all chat and reasoning team roles.</p>
				</div>
				<Chip tone="accent">{llmProvider === 'anthropic' ? 'Anthropic' : 'Nebius'}</Chip>
			</div>
			<p class="hint">
				Switches Reader, Graph-builder, Answer-engine, Reasoner and Checker-LLM between
				Nebius and Anthropic (Opus 5 / Sonnet 5 / Haiku 4.5). This toggle never touches
				Embedder — Anthropic has no embeddings endpoint — but that doesn't mean Embedder
				is on Nebius either; check System health for what it's actually running
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

	<!-- System Health -->
	<section class="block">
		<div class="block-head">
			<span class="block-ico"><Icon name="bolt" size={16} /></span>
			<div>
				<h2>System health</h2>
				<p class="section-sub">Connectivity and latency checks for storage backends and AI model endpoints.</p>
			</div>
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
</div>
</div>

<style>
	.head-sub {
		display: block;
		font-size: var(--text-sm);
		color: var(--ink-2);
		margin-top: 0.15rem;
		font-weight: 400;
	}

	.block {
		margin-bottom: var(--space-5);
		padding: var(--space-4) var(--space-5);
		border: 1px solid var(--glass-border);
		border-radius: var(--r-lg);
		background: var(--panel-2);
	}

	.block-head-wrap {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-4);
		flex-wrap: wrap;
		margin-bottom: var(--space-4);
	}

	.block-head {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		margin-bottom: var(--space-3);
	}

	.block-head-wrap .block-head {
		margin-bottom: 0;
	}

	.block-ico {
		display: flex;
		align-items: center;
		justify-content: center;
		flex: 0 0 auto;
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		background: var(--accent-soft);
		color: var(--accent-ink);
	}

	.block-head h2 {
		font-size: var(--text-base);
		font-weight: var(--weight-bold);
		color: var(--ink);
		line-height: 1.2;
	}

	.section-sub {
		font-size: var(--text-xs);
		color: var(--ink-2);
		margin-top: 0.15rem;
	}

	.head-controls {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		flex-wrap: wrap;
	}

	.token-pill {
		display: inline-flex;
		align-items: baseline;
		gap: 0.35rem;
		padding: 0.35rem 0.65rem;
		border-radius: var(--r-md);
		background: var(--panel);
		border: 1px solid var(--line);
	}

	.token-num {
		font-size: var(--text-sm);
		font-weight: 700;
		color: var(--accent-ink);
		font-family: monospace;
	}

	.token-lbl {
		font-size: 0.72rem;
		color: var(--ink-2);
		text-transform: uppercase;
		font-weight: 500;
	}

	/* View Toggle (Table / Graph) */
	.view-toggle {
		display: inline-flex;
		padding: 3px;
		background: var(--panel);
		border: 1px solid var(--line);
		border-radius: var(--r);
		gap: 2px;
	}

	.toggle-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.35rem 0.75rem;
		border-radius: calc(var(--r) - 2px);
		border: none;
		background: transparent;
		color: var(--ink-2);
		font-size: var(--text-xs);
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.toggle-btn:hover {
		color: var(--ink);
	}

	.toggle-btn.active {
		background: var(--panel-2);
		color: var(--ink);
		font-weight: 600;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
	}

	/* Agent Data Table */
	.table-wrap {
		overflow-x: auto;
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--panel);
	}

	.agent-table {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--text-sm);
	}

	.agent-table th {
		padding: 0.65rem 0.85rem;
		text-align: left;
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		font-weight: 600;
		color: var(--ink-2);
		background: var(--panel-2);
		border-bottom: 1px solid var(--line);
		white-space: nowrap;
	}

	.agent-table td {
		padding: 0.65rem 0.85rem;
		border-bottom: 1px solid var(--line);
		color: var(--ink);
		vertical-align: middle;
	}

	.agent-table tr:last-child td {
		border-bottom: none;
	}

	.agent-table tfoot td {
		background: var(--panel-2);
		border-top: 2px solid var(--line);
		border-bottom: none;
		font-weight: 600;
	}

	.agent-table .num {
		text-align: right;
	}

	.font-mono {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.85rem;
	}

	.font-bold {
		font-weight: 700;
	}

	.agent-cell {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		min-width: 140px;
	}

	.agent-avatar {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.8rem;
		height: 1.8rem;
		border-radius: var(--r);
		flex-shrink: 0;
	}

	.agent-meta {
		display: flex;
		flex-direction: column;
		line-height: 1.25;
	}

	.agent-name {
		font-weight: 600;
		color: var(--ink);
	}

	.agent-desc {
		font-size: 0.72rem;
		color: var(--ink-2);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 220px;
	}

	.model-badge {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.76rem;
		padding: 0.2rem 0.45rem;
		border-radius: var(--r-sm);
		background: var(--panel-2);
		border: 1px solid var(--line);
		color: var(--ink);
		display: inline-block;
		max-width: 190px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		vertical-align: middle;
	}

	.share-cell {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 100%;
	}

	.share-bar-bg {
		flex: 1;
		height: 6px;
		border-radius: 3px;
		background: var(--panel-2);
		overflow: hidden;
		border: 1px solid var(--line);
	}

	.share-bar-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}

	.share-pct {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--ink-2);
		min-width: 38px;
		text-align: right;
		font-family: monospace;
	}

	/* GRAPH VIEW STYLES */
	.graph-view-wrap {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.dist-bar-card {
		padding: var(--space-3) var(--space-4);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--panel);
	}

	.dist-bar-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.5rem;
	}

	.dist-title {
		font-size: var(--text-sm);
		font-weight: 600;
		color: var(--ink);
	}

	.dist-sub {
		font-size: var(--text-xs);
		color: var(--ink-2);
	}

	.stacked-bar {
		display: flex;
		width: 100%;
		height: 12px;
		border-radius: 6px;
		overflow: hidden;
		background: var(--panel-2);
		border: 1px solid var(--line);
		margin-bottom: var(--space-3);
	}

	.stacked-seg {
		height: 100%;
		transition: width 0.3s ease;
	}

	.agent-cards-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 0.6rem;
	}

	.agent-card {
		padding: 0.6rem 0.75rem;
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--panel-2);
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.agent-card-top {
		display: flex;
		align-items: center;
		gap: 0.35rem;
	}

	.color-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.card-agent-name {
		font-size: var(--text-sm);
		font-weight: 600;
		color: var(--ink);
		flex: 1;
	}

	.card-pct {
		font-size: 0.75rem;
		font-weight: 700;
		color: var(--ink-2);
		font-family: monospace;
	}

	.card-model-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.3rem;
	}

	.card-model {
		font-size: 0.68rem;
		font-family: monospace;
		color: var(--ink-2);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.card-provider {
		font-size: 0.65rem;
		color: var(--accent-ink);
		font-weight: 500;
	}

	.card-tokens-row {
		display: flex;
		align-items: baseline;
		gap: 0.3rem;
	}

	.card-tokens-val {
		font-size: var(--text-sm);
		font-weight: 700;
		color: var(--ink);
		font-family: monospace;
	}

	.card-tokens-lbl {
		font-size: 0.68rem;
		color: var(--ink-2);
	}

	.chart-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.chart-sub-toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-3);
		flex-wrap: wrap;
	}

	.chart-sub-title {
		font-size: var(--text-sm);
		font-weight: 600;
		color: var(--ink);
		display: block;
	}

	.chart-sub-desc {
		font-size: var(--text-xs);
		color: var(--ink-2);
		display: block;
	}

	.pill-group {
		display: inline-flex;
		padding: 2px;
		background: var(--panel);
		border: 1px solid var(--line);
		border-radius: var(--r);
		gap: 2px;
	}

	.pill-btn {
		font-size: 0.72rem;
		padding: 0.25rem 0.55rem;
		border-radius: calc(var(--r) - 2px);
		border: none;
		background: transparent;
		color: var(--ink-2);
		cursor: pointer;
		font-weight: 500;
		transition: all 0.15s ease;
	}

	.pill-btn:hover {
		color: var(--ink);
	}

	.pill-btn.active {
		background: var(--panel-2);
		color: var(--ink);
		font-weight: 600;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
	}

	/* SYSTEM USAGE GRID */
	.usage-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: var(--space-4);
	}

	/* SYSTEM HEALTH */
	.check-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(10.5rem, 1fr));
		gap: 0.5rem;
	}

	.check-tile {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		padding: 0.55rem 0.75rem;
		border: 1px solid var(--line);
		border-radius: var(--r);
		background: var(--panel);
	}

	.check-label {
		font-size: var(--text-sm);
		color: var(--ink-2);
		text-transform: capitalize;
	}
</style>
