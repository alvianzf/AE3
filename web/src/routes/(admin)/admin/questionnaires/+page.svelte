<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { get, post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';

	// core_store.QUESTION_TYPES (app/core_store.py) — the client portal
	// (web/src/routes/(client)/client/questionnaire/+page.svelte) already
	// renders all five; this builder used to only ever write 'text'.
	const QUESTION_TYPES = ['text', 'number', 'date', 'choice', 'multi_choice'] as const;

	type Question = {
		key: string; // local-only, for #each keying
		prompt: string;
		input_type: (typeof QUESTION_TYPES)[number];
		options: string; // comma-separated in the UI, split to an array on save
		theme: string;
	};

	let { data } = $props();
	let open = $state(false);
	// Set when editing an existing questionnaire; null means "New
	// questionnaire". Editing always creates a new version rather than
	// mutating in place (core_store.edit_questionnaire) — and, same as a
	// fresh create, that new version immediately becomes the one active
	// questionnaire, replacing whatever was active before
	// (core_store._insert_questionnaire deactivates every other row).
	let editingId = $state<string | null>(null);
	let title = $state('');
	let questions = $state<Question[]>([]);
	let submitting = $state(false);

	function blankQuestion(): Question {
		return { key: crypto.randomUUID(), prompt: '', input_type: 'text', options: '', theme: 'General' };
	}

	function openCreate() {
		editingId = null;
		title = '';
		questions = [blankQuestion()];
		open = true;
	}

	async function openEdit(id: string) {
		try {
			const q = await get(fetch, `/admin/questionnaires/${id}`);
			editingId = id;
			title = q.title;
			// Round-trips every field the backend carries — input_type,
			// options, theme — instead of flattening to prompt-only text,
			// which used to silently downgrade an already-typed/themed
			// questionnaire to plain text on resave.
			questions = (q.questions ?? []).map((qq: any) => ({
				key: crypto.randomUUID(),
				prompt: qq.prompt,
				input_type: qq.input_type ?? 'text',
				options: (qq.options ?? []).join(', '),
				theme: qq.theme || 'General'
			}));
			if (!questions.length) questions = [blankQuestion()];
			open = true;
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	function addQuestion() {
		questions = [...questions, blankQuestion()];
	}

	function removeQuestion(key: string) {
		questions = questions.filter((q) => q.key !== key);
	}

	async function save(e: Event) {
		e.preventDefault();
		submitting = true;
		const payload = questions
			.filter((q) => q.prompt.trim())
			.map((q) => ({
				prompt: q.prompt.trim(),
				input_type: q.input_type,
				theme: q.theme.trim() || 'General',
				options:
					q.input_type === 'choice' || q.input_type === 'multi_choice'
						? q.options.split(',').map((o) => o.trim()).filter(Boolean)
						: []
			}));
		try {
			await post(fetch, editingId ? `/admin/questionnaires/${editingId}` : '/admin/questionnaires', {
				title,
				questions: payload
			});
			toast(editingId ? 'New version saved and made active.' : 'Questionnaire created.');
			open = false;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Questionnaires — Admin portal</title></svelte:head>

<Spotlight title="Questionnaires">
	{#snippet actions()}
		<Button variant="filled" onclick={openCreate}>New questionnaire</Button>
	{/snippet}
	<DataTable
		columns={[{ key: 'title', label: 'Title', sortable: true }, { key: 'version', label: 'Version' }, { key: 'is_active', label: 'Active' }, { key: 'actions', label: '' }]}
		rows={data.questionnaires}
		empty="No questionnaires yet."
	>
		{#snippet row(q: any)}
			<td>{q.title}</td>
			<td>{q.version}</td>
			<td>{#if q.is_active}<Chip tone="ok">Active</Chip>{:else}No{/if}</td>
			<td><button class="edit" onclick={() => openEdit(q.id)}>Edit</button></td>
		{/snippet}
	</DataTable>
</Spotlight>

<Dialog bind:open title={editingId ? 'Edit questionnaire' : 'New questionnaire'} wide>
	<form onsubmit={save} id="qn-form">
		<TextField label="Title" bind:value={title} required />

		<div class="questions">
			{#each questions as q, i (q.key)}
				<div class="question-row">
					<div class="question-head">
						<span class="num">{i + 1}</span>
						<button type="button" class="remove" onclick={() => removeQuestion(q.key)} disabled={questions.length === 1} aria-label="Remove question">&times;</button>
					</div>
					<TextField label="Prompt" bind:value={q.prompt} required />
					<div class="question-fields">
						<div class="field">
							<label for="type-{q.key}">Type</label>
							<select id="type-{q.key}" bind:value={q.input_type}>
								{#each QUESTION_TYPES as t (t)}
									<option value={t}>{t.replaceAll('_', ' ')}</option>
								{/each}
							</select>
						</div>
						<TextField label="Theme" bind:value={q.theme} hint="Groups questions on the client's page." />
					</div>
					{#if q.input_type === 'choice' || q.input_type === 'multi_choice'}
						<TextField label="Options" bind:value={q.options} hint="Comma-separated, e.g. Never, Sometimes, Often" />
					{/if}
				</div>
			{/each}
		</div>
		<Button type="button" variant="outlined" onclick={addQuestion}>+ Add question</Button>

		{#if editingId}
			<p class="hint">Saving creates a new version and makes it the active questionnaire — clients will answer this one from now on.</p>
		{/if}
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
		<Button onclick={save} loading={submitting}>{editingId ? 'Save new version' : 'Create'}</Button>
	{/snippet}
</Dialog>

<style>
	.edit {
		font: inherit; font-size: var(--text-sm); font-weight: 650; cursor: pointer;
		border: 1px solid var(--line); background: var(--panel); color: var(--accent-ink);
		border-radius: var(--r); padding: .3rem .7rem;
	}
	.edit:hover { border-color: var(--accent); background: var(--accent-soft); }

	.questions { display: grid; gap: var(--space-4); margin: var(--space-3) 0; }
	.question-row {
		display: grid; gap: var(--space-2); padding: var(--space-3); border: 1px solid var(--line);
		border-radius: var(--r); background: var(--panel-2);
	}
	.question-head { display: flex; align-items: center; justify-content: space-between; }
	.num {
		display: inline-flex; align-items: center; justify-content: center; width: 1.5rem; height: 1.5rem;
		border-radius: 50%; background: var(--accent-soft); color: var(--accent-ink);
		font-size: var(--text-xs); font-weight: 700;
	}
	.remove {
		border: none; background: none; font-size: 1.2rem; line-height: 1; cursor: pointer; color: var(--muted);
	}
	.remove:hover:not(:disabled) { color: var(--danger); }
	.remove:disabled { opacity: .35; cursor: not-allowed; }
	.question-fields { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); }
	.field { display: flex; flex-direction: column; gap: .35rem; }
	select {
		border: 1px solid var(--line-2); border-radius: var(--r); background: var(--panel);
		padding: var(--space-3); font-size: var(--text-base); color: var(--ink); min-height: var(--tap-min);
	}
</style>
