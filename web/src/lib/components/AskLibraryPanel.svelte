<script lang="ts">
	import { onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { askLibrary, EXAMPLES } from '$lib/stores/askLibrary.svelte';

	// The dashboard's compact "Ask the Library" preview card — the full
	// conversation (and the modal that shows it) lives in the shared
	// askLibrary store / AskLibraryModal.svelte, mounted once at the
	// practitioner layout level, so this card and the global Rail button
	// drive the exact same conversation regardless of which page opened it.

	onMount(() => askLibrary.loadHistory());

	function submit(e: Event) {
		askLibrary.ask(e);
	}
</script>

<section class="ask-library block">
	<div class="al-head">
		<span class="al-ico"><Icon name="book" size={18} /></span>
		<div>
			<h2>Ask the Library</h2>
			<p>General questions — no client data</p>
		</div>
	</div>

	{#if !askLibrary.turns.length}
		<div class="al-empty">
			<p class="hint">Try asking, or type your own question below.</p>
			<div class="chip-row">
				{#each EXAMPLES as ex}
					<button type="button" class="example-chip" onclick={() => askLibrary.useExample(ex)}>{ex}</button>
				{/each}
			</div>
		</div>
	{:else}
		{@const last = askLibrary.turns[askLibrary.turns.length - 1]}
		<button type="button" class="al-preview" onclick={() => askLibrary.open()}>
			<span class="al-q">{last.question}</span>
			<span class="al-a">{(last.answer ?? '').replace(/[#*_`[\]]/g, '').slice(0, 220)}…</span>
			{#if last.searched?.length}
				<span class="al-meta">{last.searched.length} sources searched</span>
			{/if}
		</button>
	{/if}

	<form class="al-composer" onsubmit={submit}>
		<textarea
			rows="2"
			placeholder="Ask the knowledge library…"
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
</section>

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
</style>
