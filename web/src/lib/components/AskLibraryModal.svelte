<script lang="ts">
	import { renderAnswerHtml } from '$lib/markdown';
	import Icon from '$lib/components/Icon.svelte';
	import { askLibrary, AGENT_LABELS } from '$lib/stores/askLibrary.svelte';

	// Mounted once, at the practitioner layout level — reachable from
	// every page (the Rail's global "Ask the Library" button) as well as
	// from the dashboard's compact preview card, all driving the same
	// shared askLibrary store, so the conversation is the same wherever
	// it was opened from and survives navigating between pages.

	let scrollEl: HTMLDivElement | undefined = $state();

	$effect(() => {
		// Re-run whenever turns/streamingAnswer change while open, to
		// keep the newest content in view.
		void askLibrary.turns.length;
		void askLibrary.streamingAnswer;
		if (askLibrary.expanded && scrollEl) {
			const el = scrollEl;
			requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
		}
	});

	function submit(e: Event) {
		askLibrary.ask(e);
	}
</script>

{#if askLibrary.expanded}
	<div class="al-overlay" role="presentation" onclick={(e) => { if (e.target === e.currentTarget) askLibrary.close(); }}>
		<div class="al-modal">
			<div class="al-modal-head">
				<span class="al-ico"><Icon name="book" size={18} /></span>
				<div>
					<h2>Ask the Library</h2>
					<p>General questions — no client data</p>
				</div>
				<button type="button" class="al-close" onclick={() => askLibrary.close()} aria-label="Close">
					<Icon name="x" size={16} />
				</button>
			</div>
			<div class="al-thread" bind:this={scrollEl}>
				{#if !askLibrary.turns.length && !askLibrary.streamingAnswer && !askLibrary.asking}
					<p class="hint empty-text">Ask a question to get started.</p>
				{/if}
				{#each askLibrary.turns as t (t.id)}
					<div class="al-turn">
						<p class="al-turn-q">{t.question}</p>
						<div class="al-turn-a">{@html renderAnswerHtml(t.answer, new Map((t.sources ?? []).map((s: any) => [s.label, s.title])))}</div>
						{#if t.searched?.length}
							<p class="al-turn-meta">{t.searched.length} source{t.searched.length === 1 ? '' : 's'} searched</p>
						{/if}
					</div>
				{/each}
				{#if askLibrary.asking}
					<div class="al-turn">
						{#each askLibrary.steps as s}
							<div class="step" class:done={s.status === 'done'} class:error={s.status === 'error'}>
								{#if s.status === 'running'}<span class="spin" aria-hidden="true"></span>{:else}<span class="dot" aria-hidden="true"></span>{/if}
								{AGENT_LABELS[s.agent] ?? s.agent}
								{#if s.progress}<span class="hint">{s.progress}</span>{/if}
							</div>
						{/each}
						{#if askLibrary.streamingAnswer}
							<div class="al-turn-a">{@html renderAnswerHtml(askLibrary.streamingAnswer)}</div>
						{/if}
					</div>
				{/if}
			</div>
			<form class="al-composer al-composer-modal" onsubmit={submit}>
				<textarea
					rows="2"
					placeholder="Ask a follow-up…"
					bind:value={askLibrary.question}
					disabled={askLibrary.asking}
					onkeydown={(e) => {
						if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(e); }
					}}
				></textarea>
				<div class="al-composer-row">
					<div class="al-mode-toggle">
						<button type="button" class:on={askLibrary.retrievalMode === 'general_lookup'} disabled={askLibrary.asking}
							onclick={() => (askLibrary.retrievalMode = 'general_lookup')}>General lookup</button>
						<button type="button" class:on={askLibrary.retrievalMode === 'deep_research'} disabled={askLibrary.asking}
							onclick={() => (askLibrary.retrievalMode = 'deep_research')}>Deep research</button>
					</div>
					<button type="submit" class="al-send" disabled={askLibrary.asking || !askLibrary.question.trim()}>
						<Icon name="chevron" size={14} />Ask
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.al-ico {
		width: 2.25rem; height: 2.25rem; border-radius: 10px; display: grid; place-items: center;
		background: var(--accent-soft); color: var(--accent-ink); flex: 0 0 auto;
	}
	.al-overlay {
		position: fixed; inset: 0; background: rgba(0, 0, 0, .45); display: grid; place-items: center;
		z-index: 60; padding: var(--space-4);
	}
	.al-modal {
		width: min(42rem, 100%); height: min(80vh, 36rem); max-height: min(80vh, 46rem);
		display: flex; flex-direction: column; background: var(--panel); border-radius: var(--r-lg);
		box-shadow: var(--shadow); overflow: hidden;
	}
	.al-modal-head {
		display: flex; align-items: center; gap: .75rem; padding: var(--space-4) var(--space-5);
		border-bottom: 1px solid var(--line); flex: 0 0 auto;
	}
	.al-modal-head h2 { font-size: 1.05rem; font-weight: 700; color: var(--ink); letter-spacing: -.01em; margin: 0; }
	.al-modal-head p { font-size: var(--text-xs); color: var(--muted); margin: .1rem 0 0; }
	.al-modal-head > div { flex: 1 1 auto; }
	.al-close {
		border: none; background: none; color: var(--muted); cursor: pointer; padding: .4rem;
		border-radius: 8px; flex: 0 0 auto;
	}
	.al-close:hover { background: var(--panel-2); color: var(--ink); }

	.al-thread { flex: 1 1 auto; overflow-y: auto; padding: var(--space-4) var(--space-5); display: flex; flex-direction: column; gap: var(--space-5); }
	.al-turn { display: flex; flex-direction: column; gap: .4rem; }
	.al-turn-q { font-weight: 650; font-size: var(--text-sm); color: var(--ink); margin: 0; }
	.al-turn-a { font-size: var(--text-sm); color: var(--ink); line-height: 1.55; }
	.al-turn-meta { font-size: var(--text-xs); color: var(--muted); margin: 0; }
	.empty-text { text-align: center; padding: var(--space-5) 0; }

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
