<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { get } from '$lib/api';
	import { streamConsult, type RetrievalMode } from '$lib/consultStream';
	import { toast } from '$lib/stores/toast';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { renderAnswerHtml } from '$lib/markdown';

	let { data } = $props();
	let clientId = $state('');
	let clientSearch = $state('');
	const filteredClients = $derived(
		(data.clients ?? []).filter((c: any) =>
			c.name.toLowerCase().includes(clientSearch.trim().toLowerCase())
		)
	);
	const selectedClient = $derived((data.clients ?? []).find((c: any) => c.id === clientId));

	// The session this conversation continues — kept so a second "Ask"
	// actually carries the first question's context forward instead of
	// silently starting a brand-new session every time (specs/v4/04-known-
	// issues.md#h4). Cleared whenever the practitioner switches clients or
	// starts a new chat.
	let sessionId = $state('');
	let turns = $state<any[]>([]);
	let loadingHistory = $state(false);

	// GPT/Claude-style history rail: every past consultation for the
	// currently selected client, clickable to reload it into the thread.
	let sessions = $state<any[]>([]);
	let loadingSessions = $state(false);
	async function loadSessions(id: string) {
		if (!id) {
			sessions = [];
			return;
		}
		loadingSessions = true;
		try {
			// A session is created as soon as a question is sent (app/main.py's
			// /api/me/consult) but only gets a turn once the stream actually
			// finishes — an aborted request or a mid-stream crash leaves a real
			// 0-turn session row behind. Nothing to resume there, and it read
			// as broken/duplicated entries in the history list (found live) —
			// filtered out rather than shown.
			sessions = (await get(fetch, `/me/clients/${id}/sessions`)).filter((s: any) => s.turns > 0);
		} catch {
			sessions = [];
		} finally {
			loadingSessions = false;
		}
	}

	async function loadSession(id: string) {
		if (!clientId || asking) return;
		loadingHistory = true;
		try {
			const s = await get(fetch, `/me/clients/${clientId}/sessions/${id}`);
			sessionId = s.id;
			// Stored turns only have one timestamp (when the turn was written);
			// live-asked turns below track ask vs. answer separately, but that
			// distinction isn't in the database, so both map to the same value here.
			turns = (s.turns ?? []).map((t: any) => ({ asked_at: t.created_at, answered_at: t.created_at, ...t }));
		} catch {
			toast('Could not load that conversation.', 'alert');
		} finally {
			loadingHistory = false;
		}
	}

	function newChat() {
		if (asking) return;
		sessionId = '';
		turns = [];
		question = '';
	}

	onMount(async () => {
		const qClient = page.url.searchParams.get('client');
		const qSession = page.url.searchParams.get('session');
		// No auto-picking the first client in the list — landing here should
		// require an explicit choice, not silently open whoever happens to
		// sort first (found live: this looked like the page "chose" a
		// patient on your behalf, which for clinical data should never be
		// implicit). Only a real deep link (a URL that already names a
		// client) restores a selection.
		clientId = qClient ?? '';
		if (qSession && qClient) await loadSession(qSession);
	});

	// A client switch always starts a new conversation — carrying the old
	// session forward into a different client's context would be a real
	// safety issue, not a nicety. Compares against the *previous* value
	// rather than an "initialized" flag so this can't race onMount's async
	// deep-link history fetch above (whichever finishes first, the very
	// first observed clientId never counts as a "switch"). Also (re)loads
	// this client's history list, including on that first run.
	let lastClientId = '';
	$effect(() => {
		const id = clientId;
		if (lastClientId && id !== lastClientId) {
			sessionId = '';
			turns = [];
		}
		lastClientId = id;
		loadSessions(id);
	});

	// Keeps the URL in sync with which client/session is open, so a refresh
	// (or a copy-pasted link) lands back on the same conversation instead of
	// reverting to the unselected default — found live: refreshing mid-
	// conversation silently dropped back to "pick a client." replaceState,
	// not goto — this reflects state in the URL bar without a navigation or
	// reload of its own.
	//
	// Found live, 2026-09-15: on the very first arrival at this page (never
	// on a later in-app remount), the whole sidebar went unclickable —
	// every button rendered fine but did nothing. Root cause: this effect
	// ran (and called replaceState) while SvelteKit's router was still
	// mid-transition into the page; replaceState can throw in that window,
	// and an uncaught error inside a $effect breaks reactivity for the rest
	// of the component, not just this effect — which reads as "nothing is
	// clickable" with no visible error. try/catch makes this a non-fatal
	// nicety instead of a page-breaking one; building an absolute URL via
	// `new URL` (instead of a bare relative string) is also the more
	// correct way to call replaceState regardless.
	$effect(() => {
		const params = new URLSearchParams();
		if (clientId) params.set('client', clientId);
		if (sessionId) params.set('session', sessionId);
		try {
			const url = new URL(page.url);
			url.search = params.toString();
			replaceState(url, {});
		} catch {
			/* URL sync is a nicety — must never take the rest of the page down with it */
		}
	});

	let question = $state('');
	// Deep research (default): seed search + LLM-judged graph traversal —
	// thorough, slower. General lookup: one pgvector similarity query, no
	// traversal, no Neo4j round-trip — fast, less thorough. Alongside each
	// other, not a replacement (app/retrieval/general_lookup.py).
	let retrievalMode = $state<string>('deep_research');
	let asking = $state(false);
	// The question currently in flight, shown as its own chat bubble
	// immediately (GPT/Claude both echo the user's message before the
	// answer exists) instead of waiting for the SSE stream's `result` event.
	let pendingQuestion = $state('');
	let steps = $state<{ agent: string; status: 'running' | 'done' | 'error'; input_tokens?: number; output_tokens?: number; duration_s?: number; progress?: string }[]>([]);
	// Aborts the in-flight fetch if the practitioner navigates away mid-consult
	// — see the note in consultStream.ts on what this does and doesn't stop
	// server-side (specs/v4/04-known-issues.md#m4).
	let abortController: AbortController | null = null;
	onDestroy(() => abortController?.abort());

	// Practitioner-facing labels only — the underlying agent/event names
	// (seed_search, traversal, reasoner, checker) are unchanged everywhere
	// else (SSE events, step_times keys, AGENT_LABELS' own dict keys).
	const AGENT_LABELS: Record<string, string> = {
		seed_search: 'Searching', traversal: 'Connecting the dots', lookup: 'Lookup',
		reasoner: 'Answering', checker: 'Checking the facts'
	};

	const MODE_LABELS: Record<string, string> = {
		deep_research: 'Deep research', general_lookup: 'General lookup'
	};

	// The answer is rendered as sanitized Markdown ($lib/markdown.ts); [S1]/
	// [K1]… citation markers become clickable buttons within that HTML, so a
	// click on them is handled by delegation here rather than a Svelte
	// onclick per part the way the old plain-text renderer did it.
	function answerHtml(t: any) {
		const titles = new Map<string, string>((t.sources ?? []).map((s: any) => [s.label, s.title]));
		return renderAnswerHtml(t.answer, titles);
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

	function calDay(iso: string | undefined) {
		if (!iso) return '–';
		const d = new Date(iso);
		return Number.isNaN(d.getTime()) ? '–' : String(d.getDate());
	}

	function calMonth(iso: string | undefined) {
		if (!iso) return '';
		const d = new Date(iso);
		return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString([], { month: 'short' });
	}

	function failRunningSteps() {
		// Previously an error left any still-"running" step pulsing forever —
		// nothing ever marked it failed, so the UI looked like it was still
		// working on a request that had actually died (specs/v4/04-known-
		// issues.md#m3).
		steps = steps.map((s) => (s.status === 'running' ? { ...s, status: 'error' } : s));
	}

	// Chat thread auto-scrolls to the newest message/step the way GPT and
	// Claude's own web UIs do — the composer stays pinned, the transcript
	// above it scrolls, and it should follow along while streaming.
	let threadEl: HTMLDivElement | undefined;
	$effect(() => {
		turns.length; asking; steps.length; pendingQuestion;
		tick().then(() => threadEl?.scrollTo({ top: threadEl.scrollHeight, behavior: 'smooth' }));
	});

	// Recovers from a stream that never delivered its final `result`/`error`
	// event — reload from the server the same way a manual page refresh
	// would, whether the connection quietly ended with nothing or had to be
	// aborted after going stale.
	//
	// Found live, 2026-09-15: a single immediate attempt often ran *before*
	// the backend had actually finished — the checker's bounded-retry path
	// (reasoner -> checker -> retry-reasoner -> retry-checker, up to 4
	// sequential LLM calls before the stream's own `result` event) can
	// still be mid-flight when the stall watchdog fires, so the very first
	// recovery fetch found nothing and gave up, reading as "nothing
	// happened" even though the backend was seconds from finishing. Now
	// polls: the backend's own per-call ceiling (_CHAT_TIMEOUT_SECONDS,
	// app/clients/llm_client.py) is 90s, so if it hasn't produced a result
	// within a healthy margin past that, it isn't going to.
	const RECOVERY_POLL_MS = 5_000;
	const RECOVERY_MAX_MS = 90_000;
	async function recoverMissingResult() {
		const priorTurnCount = turns.length;
		const priorSessionIds = new Set(sessions.map((s) => s.id));
		const deadline = Date.now() + RECOVERY_MAX_MS;
		for (;;) {
			if (sessionId) {
				await loadSession(sessionId);
				if (turns.length > priorTurnCount) return;
			} else {
				await loadSessions(clientId);
				const found = sessions.find((s) => !priorSessionIds.has(s.id));
				if (found) {
					await loadSession(found.id);
					return;
				}
			}
			if (Date.now() >= deadline) return;
			await new Promise((r) => setTimeout(r, RECOVERY_POLL_MS));
		}
	}

	async function ask(e: Event) {
		e.preventDefault();
		if (!clientId || !question.trim() || asking) return;
		const askedQuestion = question;
		const askedAt = new Date().toISOString();
		pendingQuestion = askedQuestion;
		question = '';
		asking = true;
		steps = [];
		abortController = new AbortController();
		let gotResult = false;
		let gotError = false;
		let stalled = false;
		// Found live, deep research mode specifically: sometimes the
		// connection doesn't cleanly end at all — it just stops delivering
		// events partway through (most likely something upstream of this
		// app buffering/dropping the tail of a long-running response) and
		// the browser's fetch() sits open indefinitely, so the "stream
		// ended with nothing" recovery below never even runs. A watchdog
		// catches that case too: if too long passes with no event at all,
		// treat it as stuck and abort proactively rather than wait forever.
		let lastEventAt = Date.now();
		// 220s, not 110s — found live: the checker's bounded-retry path
		// (reasoner -> checker -> retry-reasoner -> retry-checker, up to 4
		// sequential LLM calls before the stream's own `result` event) hit
		// 117.88s end to end under real latency variance, with one single
		// phase alone spiking to 99.37s — too close to the old 110s
		// threshold for comfort. 220s stays comfortably above the worst
		// real case seen so far while still catching a genuinely dead
		// connection well before a practitioner would give up waiting on
		// their own.
		const STALL_MS = 220_000;
		const stallWatch = setInterval(() => {
			if (Date.now() - lastEventAt > STALL_MS) {
				stalled = true;
				abortController?.abort();
			}
		}, 5000);
		try {
			// Client switching is disabled while `asking` (see the disabled
			// bindings below), so clientId/sessionId can't change out from
			// under this request — no separate "which client was this for"
			// tracking needed the way a mid-flight switch would otherwise require.
			for await (const ev of streamConsult(clientId, askedQuestion, sessionId, abortController.signal, retrievalMode as RetrievalMode)) {
				lastEventAt = Date.now();
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
					gotResult = true;
					sessionId = ev.session_id;
					turns = [...turns, { question: askedQuestion, asked_at: askedAt, answered_at: new Date().toISOString(), ...ev }];
					loadSessions(clientId);
				} else if (ev.event === 'error') {
					gotError = true;
					failRunningSteps();
					toast(ev.message, 'alert');
				}
			}
			// Found live: the stream sometimes ends with neither a `result`
			// nor an `error` event — the backend had actually finished and
			// saved the turn, but the last SSE frame never reached the
			// client, so the answer only appeared after a manual page
			// refresh. Recover the same way a refresh would: reload the
			// session (or, for a brand-new one, the practitioner's now-
			// current history list) from the server instead of leaving the
			// UI stuck showing nothing.
			if (!gotResult && !gotError) await recoverMissingResult();
		} catch (err: any) {
			if (stalled) {
				// The watchdog aborted a connection that had gone quiet too
				// long — same recovery as the "stream ended with nothing"
				// case above, just reached via an explicit abort instead of
				// the loop exiting on its own.
				await recoverMissingResult();
			} else {
				failRunningSteps();
				if (err?.name !== 'AbortError') toast(err.message, 'alert');
			}
		} finally {
			clearInterval(stallWatch);
			asking = false;
			pendingQuestion = '';
			abortController = null;
		}
	}
</script>

<svelte:head><title>Consult — Practitioner portal</title></svelte:head>

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
		<!-- These are no longer in the answer above — app/main.py's
		     _strip_unsupported() cuts an unverified claim out of the text
		     rather than shipping it alongside this warning. Collapsed by
		     default, same treatment as Sources below — transparency about
		     what was removed shouldn't take up space unasked. -->
		<details class="unsupported-acc">
			<summary><Icon name="chevron" size={14} /> Removed — {t.check.unsupported.length} unverified claim{t.check.unsupported.length === 1 ? '' : 's'}</summary>
			<ul>{#each t.check.unsupported as u}<li>{u}</li>{/each}</ul>
		</details>
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
		<!-- Closed by default — the answer + citation buttons already jump into
		     this list on click, so leaving it expanded for every turn was just
		     scroll noise most of the time. -->
		<details class="sources-acc">
			<summary><Icon name="chevron" size={14} /> Sources ({t.sources.length})</summary>
			<div class="sources">
				{#each t.sources as s (s.label)}
					<div class="source" id="source-{s.label}">
						<div class="sh"><Chip tone="accent">{s.label}</Chip> {s.title} <span class="hint">{s.locator}</span></div>
						<p class="snippet">{s.snippet}</p>
					</div>
				{/each}
			</div>
		</details>
	{/if}
{/snippet}

<div class="chat-shell">
	<aside class="sidebar">
		<div class="sidebar-block">
			<div class="block-head"><Icon name="users" size={15} /><strong>Clients</strong></div>
			<div class="search-field">
				<Icon name="search" size={15} />
				<input type="search" placeholder="Search clients…" bind:value={clientSearch} disabled={asking} />
			</div>
			<ul class="clientlist">
				{#each filteredClients as c (c.id)}
					<li>
						<button class:on={clientId === c.id} disabled={asking} onclick={() => (clientId = c.id)}>{c.name}</button>
					</li>
				{:else}
					<li class="hint">No clients match.</li>
				{/each}
			</ul>
		</div>

		<div class="sidebar-block history-block">
			<div class="history-head">
				<div class="block-head"><Icon name="history" size={15} /><strong>History</strong></div>
				<button type="button" class="newchat" onclick={newChat} disabled={asking} title="New session">
					<Icon name="new-chat" size={15} />
					New session
				</button>
			</div>
			<ul class="historylist">
				{#each sessions as s (s.id)}
					<li>
						<!-- Clicking a past session loads its full transcript and keeps
						     its session_id, so the next "Ask" continues it rather than
						     starting a new one — same continuation behavior the deep-link
						     from the client detail page already relied on. -->
						<button class:on={s.id === sessionId} disabled={asking} onclick={() => loadSession(s.id)}>
							<span class="cal" aria-hidden="true">
								<span class="cal-day">{calDay(s.started_at)}</span>
								<span class="cal-month">{calMonth(s.started_at)}</span>
							</span>
							<span class="hinfo">
								<span class="htitle">{s.title ?? s.last_question ?? 'Untitled'}</span>
								<span class="hint">{s.turns} turn{s.turns === 1 ? '' : 's'}</span>
							</span>
						</button>
					</li>
				{:else}
					<li class="hint">{loadingSessions ? 'Loading…' : 'No consultations yet.'}</li>
				{/each}
			</ul>
		</div>

		{#if selectedClient}
			<div class="sidebar-block patient-widget">
				<div class="block-head"><Icon name="user-card" size={15} /><strong>Patient</strong></div>
				<p class="pname">{selectedClient.name}</p>
				<p class="hint"><Icon name="mail" size={13} />{selectedClient.email}</p>
				<dl>
					<div><dt><Icon name="calendar" size={13} /> DOB</dt><dd>{selectedClient.dob ?? '—'}</dd></div>
					<div><dt><Icon name="globe" size={13} /> Country</dt><dd>{selectedClient.country ?? '—'}</dd></div>
				</dl>
				<!-- Conditions/medications/labs shape every answer this pipeline
				     gives (app/patient/context.py) but are edited on the client's
				     own page, not here — this is a jump-to, not a duplicate form. -->
				<a class="record-link" href="/practitioner/clients/{selectedClient.id}">Edit patient record →</a>
			</div>
		{/if}
	</aside>

	<section class="chat-main">
		<div class="chat-thread" bind:this={threadEl}>
			{#if loadingHistory}
				<p class="hint empty">Loading this consultation…</p>
			{:else if !clientId}
				<div class="empty-state">
					<Icon name="users" size={28} />
					<p>Pick a client to continue</p>
					<p class="hint">Choose one from the list on the left to start or resume a consultation.</p>
				</div>
			{:else if !turns.length && !pendingQuestion}
				<p class="hint empty">Ask a question about {selectedClient?.name} to get started.</p>
			{/if}

			{#each turns as t, i (t.session_id ? `${t.session_id}-${i}` : i)}
				<div class="turn">
					<div class="bubble bubble-q">
						<p class="question">{t.question}</p>
						<div class="meta">
							{#if t.retrieval_mode}<span class="mode-tag">{MODE_LABELS[t.retrieval_mode] ?? t.retrieval_mode}</span>{/if}
							{#if t.asked_at}<span class="ts">{timeLabel(t.asked_at)}</span>{/if}
						</div>
					</div>
					<div class="bubble bubble-a">
						{@render turnView(t)}
						{#if t.retrieval_mode}<div class="meta"><span class="mode-tag">{MODE_LABELS[t.retrieval_mode] ?? t.retrieval_mode}</span></div>{/if}
					</div>
				</div>
			{/each}

			{#if pendingQuestion}
				<div class="turn">
					<div class="bubble bubble-q">
						<p class="question">{pendingQuestion}</p>
					</div>
					{#if steps.length}
						{@const s = steps[steps.length - 1]}
						<!-- One line, not a growing list — a finished step is
						     replaced by whatever's running next rather than
						     stacking underneath it (found live: the full
						     history of steps read as clutter while waiting). -->
						<div class="bubble bubble-a progress">
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
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<form class="composer" onsubmit={ask} onkeydown={(e) => {
			if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); ask(e); }
		}}>
			<div class="composer-row">
				<div class="mode-toggle" role="group" aria-label="Search mode">
					<button
						type="button" class:on={retrievalMode === 'deep_research'} disabled={asking}
						onclick={() => (retrievalMode = 'deep_research')} title="Thorough graph traversal — slower"
					><Icon name="book" size={14} /> Deep research</button>
					<button
						type="button" class:on={retrievalMode === 'general_lookup'} disabled={asking}
						onclick={() => (retrievalMode = 'general_lookup')} title="One fast similarity lookup — less thorough"
					><Icon name="bolt" size={14} /> General lookup</button>
				</div>
			</div>
			<div class="composer-row input-row">
				<TextField label="Question" type="textarea" bind:value={question} required disabled={!clientId} placeholder="Message…" />
				<Button type="submit" loading={asking}>{#if !asking}<Icon name="send" size={15} />{/if} Send</Button>
			</div>
		</form>
	</section>
</div>

<style>
	.chat-shell {
		display: grid; grid-template-columns: 18rem minmax(0, 1fr); gap: var(--space-5);
		height: calc(100dvh - var(--space-6) * 2);
	}

	/* ── Sidebar ─────────────────────────────────────────────────────── */
	/* min-width: 0 on every grid/flex item below is load-bearing, not
	   defensive boilerplate — grid/flex items default to min-width: auto,
	   which lets a long unbroken title/date string force its column wider
	   than the fixed 18rem track instead of respecting it, pushing the
	   whole sidebar into the chat column next to it (found live: the
	   composer rendered overlapping the history list). */
	.sidebar { display: grid; grid-template-rows: auto 1fr auto; gap: var(--space-4); min-height: 0; min-width: 0; }
	.sidebar-block {
		min-width: 0;
		background: var(--panel-2); border: 1px solid var(--line); border-radius: var(--r-lg);
		padding: var(--space-3); display: flex; flex-direction: column; gap: .5rem; min-height: 0;
	}
	.search-field {
		display: flex; align-items: center; gap: .4rem; padding: .4rem .6rem;
		background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--r); color: var(--muted);
	}
	.search-field input {
		border: none; background: none; flex: 1; font: inherit; color: var(--ink); min-width: 0;
	}
	.search-field input:focus { outline: none; }
	.search-field :global(svg) { flex: none; }

	.block-head { display: flex; align-items: center; gap: .4rem; color: var(--muted); }
	.block-head strong { color: var(--ink); font-size: var(--text-sm); }

	.clientlist, .historylist { list-style: none; margin: 0; padding: 0; display: grid; gap: .2rem; overflow-y: auto; }
	/* ~5 rows visible, the rest scroll — a growing client roster shouldn't
	   push the patient widget and history rail off-screen. */
	.clientlist { max-height: 12rem; }
	.clientlist button {
		width: 100%; text-align: left; border: none; background: none; padding: .5rem .6rem;
		border-radius: var(--r); cursor: pointer; font: inherit;
	}
	.clientlist button.on { background: var(--accent-soft); color: var(--accent-ink); font-weight: 650; }
	.clientlist button:disabled { opacity: .5; cursor: not-allowed; }
	.clientlist li.hint, .historylist li.hint { padding: .4rem .6rem; }

	.pname { margin: 0; font-weight: 650; font-size: var(--text-base); }
	.patient-widget .hint { margin: 0; display: flex; align-items: center; gap: .35rem; }
	.patient-widget dl { margin: .3rem 0 0; display: grid; gap: .3rem; font-size: var(--text-sm); }
	.patient-widget dl div { display: flex; justify-content: space-between; align-items: center; gap: .5rem; }
	.patient-widget dt { display: flex; align-items: center; gap: .35rem; color: var(--muted); }
	.patient-widget dd { margin: 0; font-weight: 550; }
	.record-link { display: inline-block; margin-top: var(--space-3); font-size: var(--text-sm); font-weight: 600; }

	.history-block { flex: 1 1 auto; }
	.history-head { display: flex; align-items: center; justify-content: space-between; }
	.newchat {
		display: inline-flex; align-items: center; gap: .3rem;
		padding: .3rem .6rem; border-radius: 99px; border: 1px solid var(--line-2);
		background: var(--panel); color: var(--accent-ink); cursor: pointer; font-size: var(--text-xs); font-weight: 650;
	}
	.newchat:hover:not(:disabled) { background: var(--accent-soft); }
	.newchat:disabled { opacity: .5; cursor: not-allowed; }
	.historylist button {
		width: 100%; min-width: 0; box-sizing: border-box; text-align: left; border: none; background: none;
		padding: .4rem .5rem; border-radius: var(--r); cursor: pointer; font: inherit;
		display: flex; align-items: center; gap: .55rem;
	}
	.historylist button.on { background: var(--accent-soft); }
	.historylist button:disabled { opacity: .6; cursor: not-allowed; }
	/* A calendar-app-icon-style date badge (think the iOS Calendar app: a
	   rounded square, a big bold date number, a short label) — the date on
	   a session is scannable at a glance without reading its title. Day on
	   top and big, 3-letter month underneath, every history row. */
	.cal {
		flex: none; width: 2.6rem; height: 2.6rem;
		display: flex; flex-direction: column; align-items: center; justify-content: center;
		border-radius: .65rem; background: var(--panel);
		box-shadow: 0 1px 2px rgba(0, 0, 0, .08), inset 0 0 0 1px var(--line-2);
	}
	.cal-day { font-size: 1.3rem; font-weight: 800; line-height: 1; color: var(--accent); }
	.cal-month {
		font-size: .6rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
		color: var(--muted); margin-top: .1rem;
	}
	.hinfo { min-width: 0; display: flex; flex-direction: column; gap: .1rem; }
	.htitle {
		font-size: var(--text-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
	}

	/* ── Chat column ─────────────────────────────────────────────────── */
	.chat-main {
		display: flex; flex-direction: column; min-height: 0; min-width: 0;
		background: var(--panel-2); border: 1px solid var(--line); border-radius: var(--r-lg);
	}
	.chat-thread { flex: 1 1 auto; overflow-y: auto; padding: var(--space-5); display: grid; gap: var(--space-4); align-content: start; }
	.empty { text-align: center; margin-top: var(--space-6); }
	.empty-state {
		display: flex; flex-direction: column; align-items: center; gap: .4rem;
		margin: var(--space-7) auto 0; color: var(--muted); text-align: center; max-width: 22rem;
	}
	.empty-state p { margin: 0; }
	.empty-state p:first-of-type { color: var(--ink); font-weight: 650; font-size: var(--text-base); }

	.turn { display: grid; gap: .4rem; }
	.bubble { border-radius: var(--r-lg); padding: var(--space-3) var(--space-4); max-width: 85%; }
	.bubble-q { justify-self: end; background: var(--accent); color: #fff; border-bottom-right-radius: 4px; }
	.bubble-a { justify-self: start; background: var(--panel); border: 1px solid var(--line); border-bottom-left-radius: 4px; max-width: 100%; }
	.question { margin: 0; white-space: pre-wrap; }
	.ts { font-size: var(--text-xs); color: var(--muted); white-space: nowrap; }
	/* Small label row under each bubble — which mode answered this turn,
	   plus a timestamp on the question side — not part of the message
	   content itself. */
	.meta { display: flex; align-items: center; gap: .5rem; margin-top: .4rem; }
	.bubble-q .meta { color: rgba(255, 255, 255, .75); }
	.bubble-a > .meta { margin-top: var(--space-3); padding-top: var(--space-2); border-top: 1px solid var(--line); }
	.mode-tag {
		font-size: var(--text-xs); font-weight: 650; text-transform: uppercase; letter-spacing: .03em;
		color: var(--muted);
	}
	.bubble-q .mode-tag { color: rgba(255, 255, 255, .85); }
	.rh { display: flex; align-items: center; gap: .5rem; margin-bottom: var(--space-2); }
	.rh .ts { margin-left: auto; }
	.answer { color: var(--ink-2); }
	.answer :global(p) { margin: 0 0 .6em; }
	.answer :global(p:last-child) { margin-bottom: 0; }
	.answer :global(ul), .answer :global(ol) { margin: 0 0 .6em; padding-left: 1.2rem; }
	.answer :global(h2) { font-size: var(--text-sm); text-transform: uppercase; letter-spacing: .03em; color: var(--muted); margin: 1em 0 .4em; }
	.answer :global(h2:first-child) { margin-top: 0; }
	.answer :global(code) { background: var(--panel-2); padding: .1em .3em; border-radius: 4px; font-size: .9em; }
	/* Superscript, not inline-sized — an academic-paper-style citation
	   marker (number + a short title snippet), not a full-size inline
	   token, so it reads as a reference rather than part of the sentence. */
	.answer :global(sup) { line-height: 0; }
	.answer :global(.cite) {
		font: inherit; font-weight: 650; color: var(--accent-ink); background: var(--accent-soft);
		border: none; border-radius: 4px; padding: 0 .25rem; cursor: pointer; white-space: nowrap;
	}
	.unsupported-acc { margin-top: var(--space-3); font-size: var(--text-sm); color: var(--warn); }
	.unsupported-acc summary {
		cursor: pointer; font-weight: 600; list-style: none;
		display: inline-flex; align-items: center; gap: .3rem;
	}
	.unsupported-acc summary::-webkit-details-marker { display: none; }
	.unsupported-acc summary :global(svg) { transition: transform .15s var(--ease); }
	.unsupported-acc[open] summary :global(svg) { transform: rotate(90deg); }
	.unsupported-acc ul { margin: .3rem 0 0; padding: var(--space-3); padding-left: 1.6rem; border-radius: var(--r); background: var(--warn-soft); }
	.librarian { margin-top: var(--space-4); font-size: var(--text-sm); }
	.librarian summary { cursor: pointer; color: var(--muted); font-weight: 600; }

	/* Sources: closed by default, chevron rotates open — the native
	   <details> marker is suppressed in favor of the Icon so the rotation
	   is consistent across browsers. */
	.sources-acc { margin-top: var(--space-4); font-size: var(--text-sm); }
	.sources-acc summary {
		cursor: pointer; color: var(--muted); font-weight: 600; list-style: none;
		display: inline-flex; align-items: center; gap: .3rem;
	}
	.sources-acc summary::-webkit-details-marker { display: none; }
	.sources-acc summary :global(svg) { transition: transform .15s var(--ease); }
	.sources-acc[open] summary :global(svg) { transform: rotate(90deg); }
	.sources { margin-top: var(--space-3); display: grid; gap: var(--space-3); }
	.source { padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--r); }
	.sh { display: flex; align-items: center; gap: .4rem; font-weight: 600; font-size: var(--text-sm); }
	.snippet { margin: .3rem 0 0; font-size: var(--text-sm); color: var(--muted); }
	.list { margin: .3rem 0 0; padding-left: 1.1rem; font-size: var(--text-sm); }

	.progress { display: grid; gap: .4rem; }
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

	/* ── Composer, pinned to the bottom of the chat column ──────────── */
	.composer { flex: none; border-top: 1px solid var(--line); padding: var(--space-3) var(--space-4) var(--space-4); display: grid; gap: .4rem; }
	.composer-row { display: flex; align-items: flex-end; gap: var(--space-3); }
	.composer-row :global(.field) { flex: 1; }
	.input-row :global(textarea) { min-height: 2.75rem; max-height: 10rem; }
	/* The field labels stay for screen readers, but a chat composer showing
	   "Question"/"Mode" above each control reads as a form, not a chat box —
	   visually hidden, same technique as a standard sr-only utility. */
	.composer :global(.field label) {
		position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
		overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
	}

	.mode-toggle {
		display: inline-flex; border: 1px solid var(--line-2); border-radius: 99px; padding: .15rem;
		background: var(--panel); gap: .15rem;
	}
	.mode-toggle button {
		display: inline-flex; align-items: center; gap: .35rem;
		border: none; background: none; padding: .35rem .8rem; border-radius: 99px; cursor: pointer;
		font: inherit; font-size: var(--text-sm); font-weight: 600; color: var(--muted);
	}
	.mode-toggle button.on { background: var(--accent); color: #fff; }
	.mode-toggle button:disabled { opacity: .6; cursor: not-allowed; }

	@media (max-width: 860px) {
		.chat-shell { grid-template-columns: 1fr; height: auto; }
		.sidebar { grid-template-rows: none; }
		.chat-main { height: 70dvh; }
	}
</style>
