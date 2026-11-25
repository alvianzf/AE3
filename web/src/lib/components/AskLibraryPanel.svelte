<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from '$lib/api';
	import { renderAnswerHtml } from '$lib/markdown';
	import Icon from '$lib/components/Icon.svelte';
	import {
		streamLibraryChat,
		type LibraryRetrievalMode
	} from '$lib/libraryChatStream';

	// "Ask the Library" — UX/UI design-consult recommendation, 2026-11-25:
	// deliberately plainer than per-client Consult (no avatar, no chat-
	// bubble chrome, book icon not message icon, muted accent) so the two
	// never look interchangeable — this is general-knowledge-only, no
	// client/patient data is ever involved. History IS persisted (product
	// override of the initial "ephemeral" recommendation), scoped to the
	// practitioner only.

	let turns = $state<any[]>([]);
	let loadedHistory = $state(false);
	let question = $state('');
	let asking = $state(false);
	let expanded = $state(false);
	let retrievalMode = $state<LibraryRetrievalMode>('general_lookup');
	let steps = $state<{ agent: string; status: 'running' | 'done' | 'error'; progress?: string }[]>([]);
	let streamingAnswer = $state('');
	let abortController: AbortController | null = null;
	let scrollEl: HTMLDivElement | undefined = $state();

	const AGENT_LABELS: Record<string, string> = {
		lookup: 'Searching',
		discover: 'Finding sources',
		traversal: 'Connecting the dots',
		reasoner: 'Answering',
		checker: 'Checking the facts'
	};

	const EXAMPLES = [
		'Interactions between magnesium glycinate and SSRIs',
		'Latest evidence on continuous glucose monitoring in non-diabetics',
		'Thyroid panel reference ranges across labs'
	];

	onMount(async () => {
		try {
			turns = await get(fetch, '/me/library-chat');
		} catch {
			/* dashboard still works with an empty panel if this fails */
		} finally {
			loadedHistory = true;
		}
	});

	function useExample(text: string) {
		question = text;
	}

	function scrollToBottom() {
		requestAnimationFrame(() => {
			if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
		});
	}

	async function ask(e?: Event) {
		e?.preventDefault();
		if (!question.trim() || asking) return;
		const askedQuestion = question;
		question = '';
		asking = true;
		expanded = true; // submitting always opens the full view — never grow the dashboard card in place
		steps = [];
		streamingAnswer = '';
		abortController = new AbortController();
		let gotResult = false;
		try {
			for await (const ev of streamLibraryChat(askedQuestion, retrievalMode, abortController.signal)) {
				if (ev.event === 'agent_start') {
					steps = [...steps, { agent: ev.agent, status: 'running' }];
				} else if (ev.event === 'agent_progress') {
					const progress = `hop ${ev.hop}/${ev.max_depth} · ${ev.relevant}/${ev.candidates} relevant`;
					steps = steps.map((s) => (s.agent === ev.agent && s.status === 'running' ? { ...s, progress } : s));
				} else if (ev.event === 'agent_done') {
					steps = steps.map((s) => (s.agent === ev.agent && s.status === 'running' ? { ...s, status: 'done' } : s));
				} else if (ev.event === 'answer_delta') {
					streamingAnswer += ev.text;
					scrollToBottom();
				} else if (ev.event === 'result') {
					gotResult = true;
					turns = [...turns, ev];
					streamingAnswer = '';
					scrollToBottom();
				} else if (ev.event === 'error') {
					steps = steps.map((s) => (s.status === 'running' ? { ...s, status: 'error' } : s));
					streamingAnswer = `_${ev.message}_`;
				}
			}
			if (!gotResult && !streamingAnswer) {
				streamingAnswer = '_Something went wrong. Try asking again._';
			}
		} catch (err: any) {
			if (err?.name !== 'AbortError') streamingAnswer = `_${err.message}_`;
		} finally {
			asking = false;
			steps = [];
			abortController = null;
		}
	}

	function openHistory() {
		if (turns.length) expanded = true;
	}
</script>

<section class="ask-library block" class:has-history={turns.length > 0}>
	<div class="al-head">
		<span class="al-ico"><Icon name="book" size={18} /></span>
		<div>
			<h2>Ask the Library</h2>
			<p>General questions — no client data</p>
		</div>
	</div>

	{#if !turns.length}
		<div class="al-empty">
			<p class="hint">Try asking, or type your own question below.</p>
			<div class="chip-row">
				{#each EXAMPLES as ex}
					<button type="button" class="example-chip" onclick={() => useExample(ex)}>{ex}</button>
				{/each}
			</div>
		</div>
	{:else}
		<button type="button" class="al-preview" onclick={openHistory}>
			<span class="al-q">{turns[turns.length - 1].question}</span>
			<span class="al-a">{(turns[turns.length - 1].answer ?? '').replace(/[#*_`[\]]/g, '').slice(0, 220)}…</span>
			{#if turns[turns.length - 1].searched?.length}
				<span class="al-meta">{turns[turns.length - 1].searched.length} sources searched</span>
			{/if}
		</button>
	{/if}

	<form class="al-composer" onsubmit={ask}>
		<textarea
			rows="2"
			placeholder="Ask the knowledge library…"
			bind:value={question}
			disabled={asking}
			onkeydown={(e) => {
				if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(e); }
			}}
		></textarea>
		<div class="al-composer-row">
			<div class="al-mode-toggle">
				<button type="button" class:on={retrievalMode === 'general_lookup'} disabled={asking}
					onclick={() => (retrievalMode = 'general_lookup')}>General lookup</button>
				<button type="button" class:on={retrievalMode === 'deep_research'} disabled={asking}
					onclick={() => (retrievalMode = 'deep_research')}>Deep research</button>
			</div>
			<button type="submit" class="al-send" disabled={asking || !question.trim()}>
				<Icon name="chevron" size={14} />Ask
			</button>
		</div>
	</form>
</section>

{#if expanded}
	<div class="al-overlay" role="presentation" onclick={(e) => { if (e.target === e.currentTarget) expanded = false; }}>
		<div class="al-modal">
			<div class="al-modal-head">
				<span class="al-ico"><Icon name="book" size={18} /></span>
				<div>
					<h2>Ask the Library</h2>
					<p>General questions — no client data</p>
				</div>
				<button type="button" class="al-close" onclick={() => (expanded = false)} aria-label="Close">
					<Icon name="x" size={16} />
				</button>
			</div>
			<div class="al-thread" bind:this={scrollEl}>
				{#if !turns.length && !streamingAnswer}
					<p class="hint empty-text">Ask a question to get started.</p>
				{/if}
				{#each turns as t (t.id)}
					<div class="al-turn">
						<p class="al-turn-q">{t.question}</p>
						<div class="al-turn-a">{@html renderAnswerHtml(t.answer, new Map((t.sources ?? []).map((s: any) => [s.label, s.title])))}</div>
						{#if t.searched?.length}
							<p class="al-turn-meta">{t.searched.length} source{t.searched.length === 1 ? '' : 's'} searched</p>
						{/if}
					</div>
				{/each}
				{#if asking}
					<div class="al-turn">
						{#each steps as s}
							<div class="step" class:done={s.status === 'done'} class:error={s.status === 'error'}>
								{#if s.status === 'running'}<span class="spin" aria-hidden="true"></span>{:else}<span class="dot" aria-hidden="true"></span>{/if}
								{AGENT_LABELS[s.agent] ?? s.agent}
								{#if s.progress}<span class="hint">{s.progress}</span>{/if}
							</div>
						{/each}
						{#if streamingAnswer}
							<div class="al-turn-a">{@html renderAnswerHtml(streamingAnswer)}</div>
						{/if}
					</div>
				{/if}
			</div>
			<form class="al-composer al-composer-modal" onsubmit={ask}>
				<textarea
					rows="2"
					placeholder="Ask a follow-up…"
					bind:value={question}
					disabled={asking}
					onkeydown={(e) => {
						if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(e); }
					}}
				></textarea>
				<div class="al-composer-row">
					<div class="al-mode-toggle">
						<button type="button" class:on={retrievalMode === 'general_lookup'} disabled={asking}
							onclick={() => (retrievalMode = 'general_lookup')}>General lookup</button>
						<button type="button" class:on={retrievalMode === 'deep_research'} disabled={asking}
							onclick={() => (retrievalMode = 'deep_research')}>Deep research</button>
					</div>
					<button type="submit" class="al-send" disabled={asking || !question.trim()}>
						<Icon name="chevron" size={14} />Ask
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.ask-library { display: flex; flex-direction: column; gap: var(--space-4); }
	.al-head { display: flex; align-items: center; gap: .75rem; }
	.al-ico {
		width: 2.25rem; height: 2.25rem; border-radius: 10px; display: grid; place-items: center;
		background: var(--accent-soft); color: var(--accent-ink); flex: 0 0 auto;
	}
	.al-head h2 { font-size: 1.05rem; font-weight: 700; color: var(--ink); letter-spacing: -.01em; margin: 0; }
	.al-head p { font-size: var(--text-xs); color: var(--muted); margin: .1rem 0 0; }

	.al-empty { display: flex; flex-direction: column; gap: var(--space-3); }
	.example-chip {
		border: 1px solid var(--line); background: var(--chip-neutral-bg, var(--panel-2)); color: var(--ink-2);
		border-radius: 999px; padding: .35rem .75rem; font-size: var(--text-xs); cursor: pointer; text-align: left;
		transition: border-color .15s var(--ease);
	}
	.example-chip:hover { border-color: var(--accent); }

	.al-preview {
		display: flex; flex-direction: column; gap: .25rem; text-align: left; border: 1px solid var(--line);
		background: var(--panel-2); border-radius: 12px; padding: .75rem .9rem; cursor: pointer; color: inherit;
		width: 100%; transition: border-color .15s var(--ease);
	}
	.al-preview:hover { border-color: var(--accent); }
	.al-q { font-weight: 650; font-size: var(--text-sm); color: var(--ink); }
	.al-a {
		font-size: var(--text-xs); color: var(--muted); position: relative; max-height: 3.2em; overflow: hidden;
		mask-image: linear-gradient(to bottom, #000 60%, transparent);
	}
	.al-meta { font-size: var(--text-xs); color: var(--muted); }

	.al-composer { display: flex; flex-direction: column; gap: .5rem; }
	.al-composer textarea {
		width: 100%; resize: vertical; min-height: 2.6rem; border: 1px solid var(--line); border-radius: 10px;
		background: var(--panel); color: var(--ink); padding: .55rem .7rem; font: inherit; font-size: var(--text-sm);
	}
	.al-composer-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; }
	.al-mode-toggle { display: inline-flex; border: 1px solid var(--line); border-radius: 999px; padding: 2px; }
	.al-mode-toggle button {
		border: none; background: none; color: var(--ink-2); font-size: var(--text-xs); padding: .3rem .65rem;
		border-radius: 999px; cursor: pointer;
	}
	.al-mode-toggle button.on { background: var(--accent-soft); color: var(--accent-ink); font-weight: 650; }
	.al-mode-toggle button:disabled { opacity: .6; cursor: not-allowed; }
	.al-send {
		display: inline-flex; align-items: center; gap: .35rem; border: none; background: var(--accent);
		color: #fff; font-weight: 650; font-size: var(--text-sm); padding: .45rem .9rem; border-radius: 999px;
		cursor: pointer;
	}
	.al-send:disabled { opacity: .5; cursor: not-allowed; }

	.al-overlay {
		position: fixed; inset: 0; background: rgba(0, 0, 0, .45); display: grid; place-items: center;
		z-index: 60; padding: var(--space-4);
	}
	.al-modal {
		width: min(42rem, 100%); max-height: min(80vh, 46rem); display: flex; flex-direction: column;
		background: var(--panel); border-radius: var(--r-lg); box-shadow: var(--shadow); overflow: hidden;
	}
	.al-modal-head {
		display: flex; align-items: center; gap: .75rem; padding: var(--space-4) var(--space-5);
		border-bottom: 1px solid var(--line); flex: 0 0 auto;
	}
	.al-modal-head > div { flex: 1 1 auto; }
	.al-close {
		border: none; background: none; color: var(--muted); cursor: pointer; padding: .4rem;
		border-radius: 8px; flex: 0 0 auto;
	}
	.al-close:hover { background: var(--panel-2); color: var(--ink); }

	.al-thread { flex: 1 1 auto; overflow-y: auto; padding: var(--space-4) var(--space-5); display: flex; flex-direction: column; gap: var(--space-5); }
	.al-turn { display: flex; flex-direction: column; gap: .4rem; }
	.al-turn-q { font-weight: 650; font-size: var(--text-sm); color: var(--ink); }
	.al-turn-a { font-size: var(--text-sm); color: var(--ink); line-height: 1.55; }
	.al-turn-meta { font-size: var(--text-xs); color: var(--muted); margin: 0; }
	.empty-text { text-align: center; padding: var(--space-5) 0; }

	.al-composer-modal { padding: var(--space-4) var(--space-5); border-top: 1px solid var(--line); flex: 0 0 auto; }

	.step { display: flex; align-items: center; gap: .5rem; font-size: var(--text-sm); }
	.step .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--warn); }
	.step.done .dot { background: var(--ok); }
	.step.error .dot { background: var(--danger); }
	.step .spin {
		width: 10px; height: 10px; border-radius: 50%; border: 2px solid var(--line-2);
		border-top-color: var(--accent); animation: al-spin .7s linear infinite;
	}
	@keyframes al-spin { to { transform: rotate(360deg); } }
</style>
