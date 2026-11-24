<script lang="ts">
	import Dialog from './Dialog.svelte';
	import Button from './Button.svelte';
	import { groupIntoSections } from '$lib/questionnaireSections';

	// Read-only render of an in-progress, unsaved questionnaire draft, using
	// the exact same section-grouping the live intake page uses, so a
	// practitioner sees the real themed/repeater/fixed-grid layout a client
	// will get before ever generating a link (ux-implementation-spec.md#7).
	// Input shape is the builder's own draft Question[] (comma-separated
	// options/columns/fixedRows as plain strings), normalized here to the
	// same shape the live intake page already renders.
	let {
		open = $bindable(false),
		title,
		questions
	}: {
		open?: boolean;
		title: string;
		questions: {
			prompt: string;
			input_type: string;
			options?: string;
			theme?: string;
			allowOther?: boolean;
			columns?: string;
			fixedRows?: string;
			mapsTo?: string;
		}[];
	} = $props();

	function splitList(s: string | undefined) {
		return (s ?? '').split(',').map((v) => v.trim()).filter(Boolean);
	}

	const normalized = $derived(
		questions
			.filter((q) => q.prompt.trim())
			.map((q, i) => ({
				id: String(i),
				prompt: q.prompt,
				input_type: q.input_type,
				theme: q.theme,
				options: splitList(q.options),
				allow_other: !!q.allowOther,
				columns: splitList(q.columns),
				fixed_rows: q.fixedRows ? splitList(q.fixedRows) : null,
				maps_to: q.mapsTo || null
			}))
	);
	const sections = $derived(groupIntoSections(normalized));
	const showThemeHeadings = $derived(sections.length > 1);
</script>

<Dialog bind:open title="Preview — {title}">
	<div class="preview">
		<p class="hint">This is exactly what a client sees at their link — nothing here is interactive.</p>
		{#each sections as section (section.theme)}
			<div class="section">
				{#if showThemeHeadings}<h3 class="theme">{section.theme}</h3>{/if}
				{#each section.questions as question (question.id)}
					{#if question.input_type === 'info'}
						<p class="info-text">{question.prompt}</p>
					{:else}
						<div class="question">
							<div class="prompt">{question.prompt}</div>
							{#if question.input_type === 'choice' || question.input_type === 'multi_choice'}
								<div class="pills">
									{#each question.options as opt (opt)}
										<span class="pill">{opt}</span>
									{/each}
									{#if question.allow_other}<span class="pill">Other</span>{/if}
								</div>
							{:else if question.input_type === 'repeater'}
								<div class="repeater">
									<table>
										<thead>
											<tr>
												{#if question.fixed_rows}<th></th>{/if}
												{#each question.columns as col}<th>{col}</th>{/each}
											</tr>
										</thead>
										<tbody>
											{#each question.fixed_rows ?? ['—'] as rowLabel}
												<tr>
													{#if question.fixed_rows}<td class="row-label">{rowLabel}</td>{/if}
													{#each question.columns as col}<td><span class="placeholder">{col}</span></td>{/each}
												</tr>
											{/each}
										</tbody>
									</table>
									{#if !question.fixed_rows}<span class="hint">Client can add more rows.</span>{/if}
								</div>
							{:else if question.input_type === 'file'}
								<button type="button" class="upload-placeholder" disabled>Choose file…</button>
							{:else}
								<input type="text" disabled placeholder="Client's answer appears here" />
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		{/each}
		{#if !sections.length}<p class="hint">No questions yet.</p>{/if}
	</div>
	{#snippet footer()}
		<Button variant="filled" onclick={() => (open = false)}>Close</Button>
	{/snippet}
</Dialog>

<style>
	.preview { display: grid; gap: var(--space-4); max-width: 32rem; }
	.section { display: grid; gap: var(--space-3); }
	.theme { font-size: var(--text-sm); font-weight: 650; letter-spacing: .04em; color: var(--muted); margin: 0; }
	.question { display: grid; gap: .4rem; }
	.prompt { font-weight: 600; font-size: var(--text-sm); }
	.info-text { font-size: var(--text-sm); color: var(--ink-2); font-style: italic; margin: 0; }
	.pills { display: flex; flex-wrap: wrap; gap: .4rem; }
	.pill {
		display: inline-flex; padding: .3rem .7rem; border-radius: 99px; border: 1px solid var(--line-2);
		font-size: var(--text-xs); font-weight: 650; background: var(--panel-2); color: var(--ink-2);
	}
	input[type='text'] {
		border: none; border-bottom: 1px solid var(--line-2); background: none; padding: .4rem .1rem;
		font-size: var(--text-sm); color: var(--muted);
	}
	.repeater table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
	.repeater th, .repeater td { text-align: left; padding: .3rem .5rem; border-bottom: 1px solid var(--line); }
	.row-label { font-weight: 600; }
	.placeholder { color: var(--muted); font-style: italic; }
	.upload-placeholder {
		align-self: start; border: 1px dashed var(--line-2); background: var(--panel-2); color: var(--muted);
		border-radius: var(--r); padding: .4rem 1rem; font-size: var(--text-sm); font-weight: 650;
	}
</style>
