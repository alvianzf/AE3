<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	const q = $derived(data.questionnaire);

	// input_type is one of core_store.QUESTION_TYPES: text, number, date,
	// choice, multi_choice. multi_choice answers are string[]; everything
	// else is a plain string — vault.py stores answers as opaque JSON, so
	// either shape round-trips fine.
	let answers = $state<Record<string, string | string[]>>({});
	let submitting = $state(false);

	$effect(() => {
		answers = data.response?.answers ?? {};
	});

	// Grouped in first-appearance order so a questionnaire with only the
	// default "General" theme (every one created today, since the admin
	// builder doesn't expose per-question themes yet) renders as a single
	// unheaded section rather than one redundant "General" heading.
	const sections = $derived.by(() => {
		if (!q) return [];
		const order: string[] = [];
		const byTheme = new Map<string, any[]>();
		for (const question of q.questions) {
			const theme = question.theme || 'General';
			if (!byTheme.has(theme)) { byTheme.set(theme, []); order.push(theme); }
			byTheme.get(theme)!.push(question);
		}
		return order.map((theme) => ({ theme, questions: byTheme.get(theme)! }));
	});
	const showThemeHeadings = $derived(sections.length > 1);

	function isAnswered(question: any) {
		const a = answers[question.id];
		return Array.isArray(a) ? a.length > 0 : Boolean(a && String(a).trim());
	}
	const answeredCount = $derived(q ? q.questions.filter(isAnswered).length : 0);
	const totalCount = $derived(q?.questions.length ?? 0);

	function toggleMulti(id: string, option: string) {
		const current = Array.isArray(answers[id]) ? [...(answers[id] as string[])] : [];
		const at = current.indexOf(option);
		if (at === -1) current.push(option); else current.splice(at, 1);
		answers = { ...answers, [id]: current };
	}

	async function submit(e: Event) {
		e.preventDefault();
		if (!q) return;
		submitting = true;
		try {
			await post(fetch, '/me/questionnaire', {
				questionnaire_id: q.id,
				questionnaire_version: q.version,
				answers
			});
			toast('Questionnaire submitted.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Questionnaire — Client portal</title></svelte:head>

<Spotlight title={q?.title ?? 'Questionnaire'}>
	{#if !q}
		<p class="hint">No questionnaire is active right now.</p>
	{:else}
		<div class="status-row">
			{#if data.response}
				<Chip tone="ok">Submitted</Chip>
			{:else}
				<Chip tone="neutral">Not started</Chip>
			{/if}
			<div class="progress">
				<div class="track"><div class="fill" style="width: {totalCount ? (answeredCount / totalCount) * 100 : 0}%"></div></div>
				<span class="hint">{answeredCount} of {totalCount} answered</span>
			</div>
		</div>
		{#if data.response}
			<p class="hint resubmit-note">You can update your answers any time — your practitioner sees the latest version.</p>
		{/if}

		<form onsubmit={submit}>
			{#each sections as section (section.theme)}
				<div class="section">
					{#if showThemeHeadings}<h3 class="theme">{section.theme}</h3>{/if}
					{#each section.questions as question, i (question.id)}
						<div class="question">
							<label class="prompt" for="q-{question.id}">
								<span class="num">{i + 1}</span>
								{question.prompt}
							</label>

							{#if question.input_type === 'choice'}
								<div class="pills" role="radiogroup" aria-labelledby="q-{question.id}">
									{#each question.options as opt (opt)}
										<button type="button" class="pill" class:selected={answers[question.id] === opt}
											onclick={() => (answers = { ...answers, [question.id]: opt })}>
											{opt}
										</button>
									{/each}
								</div>
							{:else if question.input_type === 'multi_choice'}
								<div class="pills">
									{#each question.options as opt (opt)}
										<button type="button" class="pill" class:selected={Array.isArray(answers[question.id]) && (answers[question.id] as string[]).includes(opt)}
											onclick={() => toggleMulti(question.id, opt)}>
											{opt}
										</button>
									{/each}
								</div>
							{:else if question.input_type === 'number'}
								<input id="q-{question.id}" type="number" bind:value={answers[question.id]} />
							{:else if question.input_type === 'date'}
								<input id="q-{question.id}" type="date" bind:value={answers[question.id]} />
							{:else}
								<textarea id="q-{question.id}" bind:value={answers[question.id]} rows="3"></textarea>
							{/if}
						</div>
					{/each}
				</div>
			{/each}
			<Button type="submit" loading={submitting}>{data.response ? 'Save changes' : 'Submit answers'}</Button>
		</form>
	{/if}
</Spotlight>

<style>
	.status-row { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; margin-bottom: var(--space-5); }
	.progress { display: flex; align-items: center; gap: var(--space-3); flex: 1 1 12rem; }
	.track { flex: 1 1 auto; height: 6px; border-radius: 99px; background: var(--panel-2); min-width: 6rem; }
	.fill { height: 100%; border-radius: 99px; background: var(--accent); transition: width .25s var(--ease); }
	.progress .hint { white-space: nowrap; }
	.resubmit-note { margin-top: -.75rem; margin-bottom: var(--space-4); }

	form { display: grid; gap: var(--space-6); }
	.section { display: grid; gap: var(--space-4); }
	.theme {
		font-size: var(--text-sm); font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
		color: var(--muted); border-bottom: 1px solid var(--line); padding-bottom: .4rem;
	}
	.question { display: grid; gap: .6rem; }
	.prompt { display: flex; align-items: baseline; gap: .6rem; font-weight: 650; }
	.num {
		flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center;
		width: 1.5rem; height: 1.5rem; border-radius: 50%; background: var(--accent-soft);
		color: var(--accent-ink); font-size: var(--text-xs); font-weight: 700;
	}

	textarea, input[type='number'], input[type='date'] {
		border: 1px solid var(--line-2); border-radius: var(--r); background: var(--panel);
		padding: var(--space-3); font: inherit; color: var(--ink); min-height: var(--tap-min);
		transition: border-color .15s var(--ease), box-shadow .15s var(--ease);
	}
	textarea:focus, input:focus {
		outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);
	}

	.pills { display: flex; flex-wrap: wrap; gap: .5rem; }
	.pill {
		font: inherit; font-size: var(--text-sm); font-weight: 600; cursor: pointer;
		border: 1px solid var(--line-2); background: var(--panel); color: var(--ink);
		border-radius: 99px; padding: .5rem 1.1rem; min-height: var(--tap-min);
		transition: border-color .15s var(--ease), background .15s var(--ease), color .15s var(--ease);
	}
	.pill:hover { border-color: var(--accent); }
	.pill.selected { border-color: var(--accent); background: var(--accent); color: #fff; }
</style>
