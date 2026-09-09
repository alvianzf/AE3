<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { get } from '$lib/api';
	import { streamConsult } from '$lib/consultStream';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import Select from '$lib/components/Select.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';

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
				turns = s.turns ?? [];
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
	let asking = $state(false);
	let steps = $state<{ agent: string; status: 'running' | 'done'; input_tokens?: number; output_tokens?: number }[]>([]);

	const AGENT_LABELS: Record<string, string> = {
		librarian: 'Librarian', specialist: 'Specialist', checker: 'Checker'
	};

	// Splits the answer text on [S1]/[S2]… markers so each one that matches a
	// real source in `sources` renders as a clickable jump-to-citation button
	// instead of inert text — the markers were previously rendered literally
	// with nothing to click and no source panel to click into.
	function citationParts(text: string, sources: any[]) {
		const labels = new Set((sources ?? []).map((s) => s.label));
		const parts: { text?: string; cite?: string }[] = [];
		const re = /\[(S\d+)\]/g;
		let last = 0;
		let m: RegExpExecArray | null;
		while ((m = re.exec(text))) {
			if (m.index > last) parts.push({ text: text.slice(last, m.index) });
			if (labels.has(m[1])) parts.push({ cite: m[1] });
			else parts.push({ text: m[0] });
			last = re.lastIndex;
		}
		if (last < text.length) parts.push({ text: text.slice(last) });
		return parts;
	}

	function jumpToSource(label: string) {
		document.getElementById(`source-${label}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
	}

	async function ask(e: Event) {
		e.preventDefault();
		if (!clientId || !question.trim() || asking) return;
		const askedQuestion = question;
		asking = true;
		steps = [];
		try {
			// Client switching is disabled while `asking` (see the disabled
			// bindings below), so clientId/sessionId can't change out from
			// under this request — no separate "which client was this for"
			// tracking needed the way a mid-flight switch would otherwise require.
			for await (const ev of streamConsult(clientId, askedQuestion, sessionId)) {
				if (ev.event === 'agent_start') {
					steps = [...steps, { agent: ev.agent, status: 'running' }];
				} else if (ev.event === 'agent_done') {
					steps = steps.map((s) =>
						s.agent === ev.agent && s.status === 'running'
							? { ...s, status: 'done', input_tokens: ev.input_tokens, output_tokens: ev.output_tokens }
							: s
					);
				} else if (ev.event === 'result') {
					sessionId = ev.session_id;
					turns = [...turns, { question: askedQuestion, ...ev }];
					question = '';
				} else if (ev.event === 'error') {
					toast(ev.message, 'alert');
				}
			}
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			asking = false;
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
		</div>
		<p>
			{#each citationParts(t.answer, t.sources) as part}
				{#if part.cite}<button type="button" class="cite" onclick={() => jumpToSource(part.cite as string)}>[{part.cite}]</button>{:else}{part.text}{/if}
			{/each}
		</p>

		{#if t.check?.unsupported?.length}
			<div class="unsupported">
				<strong>Claims the check could not verify:</strong>
				<ul>{#each t.check.unsupported as u}<li>{u}</li>{/each}</ul>
			</div>
		{/if}

		{#if t.librarian}
			<details class="librarian">
				<summary>How the librarian chose — considered {t.librarian.considered}, opened {t.librarian.opened?.length ?? 0}{#if t.librarian.truncated}, {t.librarian.truncated} truncated{/if}</summary>
				{#if t.librarian.reasoning}<p class="hint">{t.librarian.reasoning}</p>{/if}
				{#if t.librarian.opened?.length}
					<ul class="list">
						{#each t.librarian.opened as o}<li>{o.title} <Chip tone="neutral">grade {o.grade}</Chip></li>{/each}
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
			<TextField label="Question" type="textarea" bind:value={question} required placeholder="What would you like to know?" />
			<Button type="submit" loading={asking}>Ask</Button>
		</form>

		{#if loadingHistory}
			<p class="hint" style="margin-top: var(--space-4)">Loading this consultation…</p>
		{/if}

		{#if steps.length}
			<div class="progress">
				{#each steps as s (s.agent)}
					<div class="step" class:done={s.status === 'done'}>
						<span class="dot" aria-hidden="true"></span>
						{AGENT_LABELS[s.agent] ?? s.agent}
						{#if s.status === 'done'}
							<Chip tone="neutral">{s.input_tokens}→{s.output_tokens} tok</Chip>
						{:else}
							<span class="hint">running…</span>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		{#if turns.length}
			<div class="thread">
				{#each turns as t, i (t.session_id ? `${t.session_id}-${i}` : i)}
					<div class="turn">
						<p class="question">{t.question}</p>
						{@render turnView(t)}
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
	.step.done .dot { background: var(--ok); animation: none; }
	.thread { display: grid; gap: var(--space-5); margin-top: var(--space-5); }
	.turn { padding-top: var(--space-4); border-top: 1px solid var(--glass-line); }
	.question { font-weight: 650; margin: 0 0 var(--space-2); }
	.rh { display: flex; gap: .5rem; margin-bottom: var(--space-2); }
	.cite {
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
