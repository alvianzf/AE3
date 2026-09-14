<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { get } from '$lib/api';
	import { streamConsult, type RetrievalMode } from '$lib/consultStream';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import Select from '$lib/components/Select.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import { renderAnswerHtml } from '$lib/markdown';

	let { data } = $props();
	let clientId = $state('');
	// The session this conversation continues — kept so a second "Ask"
	// actually carries the first question's context forward instead of
	// silently starting a brand-new session every time (specs/v4/04-known-
	// issues.md#h4). Cleared whenever the practitioner switches clients.
	let sessionId = $state('');
	let turns = $state<any[]>([]);
	let loadingHistory = $state(false);

	onMount(async () => {
		const qClient = page.url.searchParams.get('client');
		const qSession = page.url.searchParams.get('session');
		clientId = qClient ?? data.clients[0]?.id ?? '';
		if (qSession && qClient) {
			loadingHistory = true;
			try {
				const s = await get(fetch, `/me/clients/${qClient}/sessions/${qSession}`);
				sessionId = s.id;
				// Stored turns only have one timestamp (when the turn was written);
				// live-asked turns above track ask vs. answer separately, but that
				// distinction isn't in the database, so both map to the same value here.
				turns = (s.turns ?? []).map((t: any) => ({ asked_at: t.created_at, answered_at: t.created_at, ...t }));
			} catch {
				/* the linked session no longer exists or isn't this practitioner's — start fresh */
			} finally {
				loadingHistory = false;
			}
		}
	});

	// A client switch (button or the Select) always starts a new
	// conversation — carrying the old session forward into a different
	// client's context would be a real safety issue, not a nicety. Compares
	// against the *previous* value rather than an "initialized" flag so this
	// can't race onMount's async deep-link history fetch above (whichever
	// finishes first, the very first observed clientId never counts as a
	// "switch").
	let lastClientId = '';
	$effect(() => {
		const id = clientId;
		if (lastClientId && id !== lastClientId) {
			sessionId = '';
			turns = [];
		}
		lastClientId = id;
	});

	let question = $state('');
	// Deep research (default): seed search + LLM-judged graph traversal —
	// thorough, slower. General lookup: one pgvector similarity query, no
	// traversal, no Neo4j round-trip — fast, less thorough. Alongside each
	// other, not a replacement (app/retrieval/general_lookup.py).
	let retrievalMode = $state<string>('deep_research');
	let asking = $state(false);
	let steps = $state<{ agent: string; status: 'running' | 'done' | 'error'; input_tokens?: number; output_tokens?: number; duration_s?: number; progress?: string }[]>([]);
	// Aborts the in-flight fetch if the practitioner navigates away mid-consult
	// — see the note in consultStream.ts on what this does and doesn't stop
	// server-side (specs/v4/04-known-issues.md#m4).
	let abortController: AbortController | null = null;
	onDestroy(() => abortController?.abort());

	const AGENT_LABELS: Record<string, string> = {
		seed_search: 'Seed search', traversal: 'Graph traversal', lookup: 'Lookup',
		reasoner: 'Reasoner', checker: 'Checker'
	};

	// The answer is rendered as sanitized Markdown ($lib/markdown.ts); [S1]/
	// [K1]… citation markers become clickable buttons within that HTML, so a
	// click on them is handled by delegation here rather than a Svelte
	// onclick per part the way the old plain-text renderer did it.
	function answerHtml(t: any) {
		const labels = new Set<string>((t.sources ?? []).map((s: any) => s.label));
		return renderAnswerHtml(t.answer, labels);
	}

	function onAnswerClick(e: MouseEvent) {
		const btn = (e.target as HTMLElement).closest('.cite') as HTMLElement | null;
		if (!btn) return;
		document.getElementById(`source-${btn.dataset.cite}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
	}

	function timeLabel(iso: string | number | undefined) {
		if (!iso) return '';
		const d = new Date(iso);
		return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}

	function failRunningSteps() {
		// Previously an error left any still-"running" step pulsing forever —
		// nothing ever marked it failed, so the UI looked like it was still
		// working on a request that had actually died (specs/v4/04-known-
		// issues.md#m3).
		steps = steps.map((s) => (s.status === 'running' ? { ...s, status: 'error' } : s));
	}

	async function ask(e: Event) {
		e.preventDefault();
		if (!clientId || !question.trim() || asking) return;
		const askedQuestion = question;
		const askedAt = new Date().toISOString();
		asking = true;
		steps = [];
		abortController = new AbortController();
		try {
			// Client switching is disabled while `asking` (see the disabled
			// bindings below), so clientId/sessionId can't change out from
			// under this request — no separate "which client was this for"
			// tracking needed the way a mid-flight switch would otherwise require.
			for await (const ev of streamConsult(clientId, askedQuestion, sessionId, abortController.signal, retrievalMode as RetrievalMode)) {
				if (ev.event === 'agent_start') {
					steps = [...steps, { agent: ev.agent, status: 'running' }];
				} else if (ev.event === 'agent_progress') {
					// A traversal hop is a real ~60-100s round-trip each — without
					// this, "running…" sat unchanged for the whole multi-minute
					// span, indistinguishable from the request actually being stuck.
					const progress = `hop ${ev.hop}/${ev.max_depth} · ${ev.relevant}/${ev.candidates} relevant · ${ev.duration_s}s`;
					steps = steps.map((s) =>
						s.agent === ev.agent && s.status === 'running' ? { ...s, progress } : s
					);
				} else if (ev.event === 'agent_done') {
					steps = steps.map((s) =>
						s.agent === ev.agent && s.status === 'running'
							? { ...s, status: 'done', input_tokens: ev.input_tokens, output_tokens: ev.output_tokens, duration_s: ev.duration_s }
							: s
					);
				} else if (ev.event === 'result') {
					sessionId = ev.session_id;
					turns = [...turns, { question: askedQuestion, asked_at: askedAt, answered_at: new Date().toISOString(), ...ev }];
					question = '';
				} else if (ev.event === 'error') {
					failRunningSteps();
					toast(ev.message, 'alert');
				}
			}
		} catch (err: any) {
			failRunningSteps();
			if (err?.name !== 'AbortError') toast(err.message, 'alert');
		} finally {
			asking = false;
			abortController = null;
		}
	}
</script>

<svelte:head><title>Consult — Practitioner portal</title></svelte:head>

<div class="layout">
	<Quiet title="Client">
		<ul class="clientlist">
			{#each data.clients as c (c.id)}
				<li>
					<button class:on={clientId === c.id} disabled={asking} onclick={() => (clientId = c.id)}>{c.name}</button>
				</li>
			{:else}
				<li class="hint">No clients yet.</li>
			{/each}
		</ul>
	</Quiet>

	{#snippet turnView(t: any)}
		<div class="rh">
			{#if t.check?.verdict}
				<Chip tone={t.check.verdict === 'pass' ? 'ok' : 'warn'}>{t.check.verdict}</Chip>
			{:else}
				<Chip tone="neutral">not independently checked</Chip>
			{/if}
			{#if t.revised}<Chip tone="accent">revised</Chip>{/if}
			{#if t.total_time_s}<Chip tone="neutral">{t.total_time_s}s total</Chip>{/if}
			{#if t.answered_at}<span class="ts">{timeLabel(t.answered_at)}</span>{/if}
		</div>
		<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
		<div class="answer" onclick={onAnswerClick}>{@html answerHtml(t)}</div>

		{#if t.check?.unsupported?.length}
			<div class="unsupported">
				<strong>Claims the check could not verify:</strong>
				<ul>{#each t.check.unsupported as u}<li>{u}</li>{/each}</ul>
			</div>
		{/if}

		{#if t.traversal}
			<!-- specs/v5 replaced the Librarian-picks-then-traverses pipeline
			     with graph traversal + per-hop pruning; this panel reads the
			     new result shape (seed_search/traversal) instead of the
			     retired `librarian` key. -->
			<details class="librarian">
				<summary>
					How it searched
					{#if t.seed_search}— seed query {JSON.stringify(t.seed_search.search_query)}, {t.seed_search.seed_count} seed node(s){/if},
					traversal reached depth {t.traversal.depth_reached} ({t.traversal.stopped_reason.replaceAll('_', ' ')})
				</summary>
				{#if t.step_times}
					<p class="hint">
						{#each Object.entries(t.step_times) as [agent, seconds]}
							{AGENT_LABELS[agent] ?? agent}: {seconds}s&nbsp;&nbsp;
						{/each}
					</p>
				{/if}
				{#if t.traversal.path?.length}
					<ul class="list">
						{#each t.traversal.path as p}
							<li>
								<Chip tone={p.relevant ? 'accent' : 'neutral'}>{p.relevant ? 'kept' : 'dropped'}</Chip>
								hop {p.hop} — {p.label}
								{#if p.reason}<span class="hint">— {p.reason}</span>{/if}
							</li>
						{/each}
					</ul>
				{/if}
			</details>
		{/if}

		{#if t.sources?.length}
			<div class="sources">
				<strong>Sources</strong>
				{#each t.sources as s (s.label)}
					<div class="source" id="source-{s.label}">
						<div class="sh"><Chip tone="accent">{s.label}</Chip> {s.title} <span class="hint">{s.locator}</span></div>
						<p class="snippet">{s.snippet}</p>
					</div>
				{/each}
			</div>
		{/if}
	{/snippet}

	<!-- Tier 1 + leafmark: the ask panel is the reason this page exists (specs/v4/03, kept from v3) -->
	<Spotlight title="Ask about this client" leaf>
		<form onsubmit={ask}>
			<Select label="Client" bind:value={clientId} disabled={asking} options={data.clients.map((c: any) => ({ value: c.id, label: c.name }))} />
			<Select
				label="Mode"
				bind:value={retrievalMode}
				disabled={asking}
				options={[
					{ value: 'deep_research', label: 'Deep research — thorough, slower' },
					{ value: 'general_lookup', label: 'General lookup — fast, less thorough' }
				]}
			/>
			<TextField label="Question" type="textarea" bind:value={question} required placeholder="What would you like to know?" />
			<Button type="submit" loading={asking}>Ask</Button>
		</form>

		{#if loadingHistory}
			<p class="hint" style="margin-top: var(--space-4)">Loading this consultation…</p>
		{/if}

		{#if steps.length}
			<div class="progress">
				{#each steps as s (s.agent)}
					<div class="step" class:done={s.status === 'done'} class:error={s.status === 'error'}>
						{#if s.status === 'running'}
							<span class="spin" aria-hidden="true"></span>
						{:else}
							<span class="dot" aria-hidden="true"></span>
						{/if}
						{AGENT_LABELS[s.agent] ?? s.agent}
						{#if s.status === 'done'}
							<Chip tone="neutral">{s.input_tokens}→{s.output_tokens} tok · {s.duration_s}s</Chip>
						{:else if s.status === 'error'}
							<span class="hint">failed</span>
						{:else}
							<span class="hint">{s.progress ?? 'running…'}</span>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		{#if turns.length}
			<div class="thread">
				{#each turns as t, i (t.session_id ? `${t.session_id}-${i}` : i)}
					<div class="turn">
						<div class="bubble bubble-q">
							<p class="question">{t.question}</p>
							{#if t.asked_at}<span class="ts">{timeLabel(t.asked_at)}</span>{/if}
						</div>
						<div class="bubble bubble-a">
							{@render turnView(t)}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</Spotlight>
</div>

<style>
	.layout { display: grid; grid-template-columns: 16rem 1fr; gap: var(--space-5); align-items: start; }
	.clientlist { list-style: none; margin: 0; padding: 0; display: grid; gap: .25rem; }
	.clientlist button {
		width: 100%; text-align: left; border: none; background: none; padding: .5rem .6rem;
		border-radius: var(--r); cursor: pointer; font: inherit;
	}
	.clientlist button.on { background: var(--accent-soft); color: var(--accent-ink); font-weight: 650; }
	.clientlist button:disabled { opacity: .5; cursor: not-allowed; }
	form { display: grid; gap: var(--space-3); }
	.progress { margin-top: var(--space-4); display: grid; gap: .4rem; }
	.step { display: flex; align-items: center; gap: .5rem; font-size: var(--text-sm); }
	.step .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--warn); animation: breathe 1s ease-in-out infinite; }
	.step .spin {
		width: .8rem; height: .8rem; border-radius: 50%; border: 2px solid var(--warn);
		border-top-color: transparent; animation: spin .7s linear infinite; flex: none;
	}
	.step.done .dot { background: var(--ok); animation: none; }
	.step.error .dot { background: var(--danger); animation: none; }
	.step.error .hint { color: var(--danger); }
	@keyframes spin { to { transform: rotate(360deg); } }

	.thread { display: grid; gap: var(--space-4); margin-top: var(--space-5); }
	.turn { display: grid; gap: .4rem; padding-top: var(--space-4); border-top: 1px solid var(--glass-line); }
	.bubble { border-radius: var(--r-lg); padding: var(--space-3) var(--space-4); max-width: 85%; }
	.bubble-q {
		justify-self: end; background: var(--accent); color: #fff;
		border-bottom-right-radius: 4px; display: flex; align-items: baseline; gap: .6rem;
	}
	.bubble-q .ts { color: rgba(255, 255, 255, .75); }
	.bubble-a { justify-self: start; background: var(--panel-2); border: 1px solid var(--line); border-bottom-left-radius: 4px; max-width: 100%; }
	.question { margin: 0; }
	.ts { font-size: var(--text-xs); color: var(--muted); white-space: nowrap; }
	.rh { display: flex; align-items: center; gap: .5rem; margin-bottom: var(--space-2); }
	.rh .ts { margin-left: auto; }
	.answer :global(p) { margin: 0 0 .6em; }
	.answer :global(p:last-child) { margin-bottom: 0; }
	.answer :global(ul), .answer :global(ol) { margin: 0 0 .6em; padding-left: 1.2rem; }
	.answer :global(h2) { font-size: var(--text-sm); text-transform: uppercase; letter-spacing: .03em; color: var(--muted); margin: 1em 0 .4em; }
	.answer :global(h2:first-child) { margin-top: 0; }
	.answer :global(code) { background: var(--panel); padding: .1em .3em; border-radius: 4px; font-size: .9em; }
	.answer :global(.cite) {
		font: inherit; font-weight: 650; color: var(--accent-ink); background: var(--accent-soft);
		border: none; border-radius: 4px; padding: 0 .3rem; cursor: pointer;
	}
	.unsupported { margin-top: var(--space-3); padding: var(--space-3); border-radius: var(--r); background: var(--warn-soft); color: var(--warn); font-size: var(--text-sm); }
	.unsupported ul { margin: .3rem 0 0; padding-left: 1.1rem; }
	.librarian { margin-top: var(--space-4); font-size: var(--text-sm); }
	.librarian summary { cursor: pointer; color: var(--muted); font-weight: 600; }
	.sources { margin-top: var(--space-4); display: grid; gap: var(--space-3); }
	.source { padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--r); }
	.sh { display: flex; align-items: center; gap: .4rem; font-weight: 600; font-size: var(--text-sm); }
	.snippet { margin: .3rem 0 0; font-size: var(--text-sm); color: var(--muted); }
	.list { margin: .3rem 0 0; padding-left: 1.1rem; font-size: var(--text-sm); }
	@media (max-width: 860px) { .layout { grid-template-columns: 1fr; } }
</style>
