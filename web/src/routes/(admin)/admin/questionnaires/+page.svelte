<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { get, post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import DataTable from '$lib/components/DataTable.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	// core_store.QUESTION_TYPES (app/core_store.py) — the client portal
	// (web/src/routes/(client)/client/questionnaire/+page.svelte) already
	// renders all five; this builder used to only ever write 'text'.
	const QUESTION_TYPES = ['text', 'number', 'date', 'choice', 'multi_choice'] as const;
	// Mirrors the practitioner builder's own MAPS_TO_FIELDS
	// (web/src/routes/(practitioner)/practitioner/questionnaires) — only
	// meaningful on an 'initial'-kind questionnaire, same backend contract
	// (core_store._insert_questionnaire requires exactly one client_name
	// and one client_email mapped question for that kind).
	const MAPS_TO_FIELDS = ['', 'client_name', 'client_email', 'client_dob', 'client_country'] as const;

	type Question = {
		key: string; // local-only, for #each keying
		prompt: string;
		input_type: (typeof QUESTION_TYPES)[number];
		options: string; // comma-separated in the UI, split to an array on save
		theme: string;
		mapsTo: string;
	};

	let { data } = $props();
	let open = $state(false);
	// Which link kind this (site-wide default) questionnaire is for — same
	// choice the practitioner builder already offers, backed by the same
	// `kind` field; an admin default can be a new-client intake too, not
	// just a follow-up.
	let qKind = $state<'initial' | 'followup'>('followup');
	// Set when editing an existing questionnaire; null means "New
	// questionnaire". Editing always creates a new version rather than
	// mutating in place (core_store.edit_questionnaire) — and, same as a
	// fresh create, that new version immediately becomes the active one
	// *within its own scope* (the admin default, or one practitioner's own
	// set), replacing whatever was active in that scope before
	// (core_store._insert_questionnaire's deactivation is now scoped by
	// practitioner_id, not global — a practitioner's own questionnaires and
	// the admin default deactivate independently of each other).
	let editingId = $state<string | null>(null);
	let title = $state('');
	let questions = $state<Question[]>([]);
	let submitting = $state(false);

	function blankQuestion(): Question {
		return { key: crypto.randomUUID(), prompt: '', input_type: 'text', options: '', theme: 'General', mapsTo: '' };
	}

	function mappedQuestion(prompt: string, mapsTo: string, inputType: Question['input_type'] = 'text'): Question {
		return { ...blankQuestion(), prompt, input_type: inputType, mapsTo };
	}

	// Same reasoning as the practitioner builder's own onKindChange: an
	// 'initial' questionnaire needs exactly one client_name and one
	// client_email question before it can save at all, so pre-fill the
	// four client fields (still fully editable/removable) the moment this
	// switches to 'initial', rather than make the practitioner discover
	// the requirement by hitting the save error. Never clobbers real
	// content — only fires when nothing's mapped yet.
	function onKindChange() {
		if (qKind !== 'initial') return;
		if (questions.some((q) => q.mapsTo)) return;
		const onlyBlank = questions.length === 1 && !questions[0].prompt.trim();
		const starter = [
			mappedQuestion('Full name', 'client_name'),
			mappedQuestion('Email', 'client_email'),
			mappedQuestion('Date of birth', 'client_dob', 'date'),
			mappedQuestion('Country', 'client_country')
		];
		questions = onlyBlank ? starter : [...starter, ...questions];
	}

	function openCreate() {
		editingId = null;
		title = '';
		qKind = 'followup';
		questions = [blankQuestion()];
		open = true;
	}

	async function openEdit(id: string) {
		try {
			const q = await get(fetch, `/admin/questionnaires/${id}`);
			editingId = id;
			title = q.title;
			qKind = q.kind === 'initial' ? 'initial' : 'followup';
			// Round-trips every field the backend carries — input_type,
			// options, theme — instead of flattening to prompt-only text,
			// which used to silently downgrade an already-typed/themed
			// questionnaire to plain text on resave.
			questions = (q.questions ?? []).map((qq: any) => ({
				key: crypto.randomUUID(),
				prompt: qq.prompt,
				input_type: qq.input_type ?? 'text',
				options: (qq.options ?? []).join(', '),
				theme: qq.theme || 'General',
				mapsTo: qq.maps_to || ''
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

	async function setActive(id: string, active: boolean) {
		try {
			await post(fetch, `/admin/questionnaires/${id}/${active ? 'activate' : 'deactivate'}`);
			toast(active ? 'Questionnaire activated.' : 'Questionnaire deactivated.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
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
						: [],
				maps_to: qKind === 'initial' && q.mapsTo ? q.mapsTo : null
			}));
		try {
			await post(fetch, editingId ? `/admin/questionnaires/${editingId}` : '/admin/questionnaires', {
				title,
				kind: qKind,
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

<div class="pane-row"><div class="detail-pane"><div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="clipboard" size={16} /></span><h1>Questionnaires</h1></div><div class="head-actions">{@render actions()}</div></div>
	{#snippet actions()}
		<Button variant="filled" onclick={openCreate}><Icon name="plus" size={15} />New questionnaire</Button>
	{/snippet}
	<DataTable
		columns={[{ key: 'title', label: 'Title', sortable: true }, { key: 'owner', label: 'Owner' }, { key: 'kind', label: 'Kind' }, { key: 'version', label: 'Version' }, { key: 'is_active', label: 'Active' }, { key: 'actions', label: '' }]}
		rows={data.questionnaires}
		empty="No questionnaires yet."
	>
		{#snippet row(q: any)}
			<td>{q.title}</td>
			<td>{q.owner_name ? `Practitioner: ${q.owner_name}` : 'Admin default'}</td>
			<td>{q.kind === 'initial' ? 'New client' : 'Follow-up'}</td>
			<td>{q.version}</td>
			<td>{#if q.is_active}<Chip tone="ok">Active</Chip>{:else}No{/if}</td>
			<td class="actions">
				<button class="edit" onclick={() => openEdit(q.id)}><Icon name="edit" size={14} />Edit</button>
				{#if q.is_active}
					<Button variant="text" onclick={() => setActive(q.id, false)}><Icon name="pause" size={15} />Deactivate</Button>
				{:else}
					<Button variant="text" onclick={() => setActive(q.id, true)}><Icon name="play" size={15} />Activate</Button>
				{/if}
			</td>
		{/snippet}
	</DataTable>
</div></div>

<Dialog bind:open title={editingId ? 'Edit questionnaire' : 'New questionnaire'} wide>
	<form onsubmit={save} id="qn-form">
		<TextField label="Title" bind:value={title} required />

		<div class="field">
			<label for="qn-kind">Who answers this, via a link</label>
			<select id="qn-kind" bind:value={qKind} onchange={onKindChange}>
				<option value="followup">An existing client (follow-up)</option>
				<option value="initial">Someone with no client record yet (new intake)</option>
			</select>
		</div>
		{#if qKind === 'initial'}
			<p class="hint">Mark one question "Maps to → Client name" and one "Maps to → Client email" below — submitting a link for this questionnaire creates the client record from those two answers.</p>
		{/if}

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
					{#if qKind === 'initial'}
						<div class="field">
							<label for="maps-{q.key}">Maps to (new-client field)</label>
							<select id="maps-{q.key}" bind:value={q.mapsTo}>
								{#each MAPS_TO_FIELDS as f (f)}
									<option value={f}>{f ? f.replace('client_', 'Client ') : '— none —'}</option>
								{/each}
							</select>
						</div>
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
	.actions { display: flex; align-items: center; gap: .25rem; }
	.edit {
		display: inline-flex; align-items: center; gap: .35rem;
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
		border: none; border-bottom: 1px solid var(--line-2); border-radius: 0; background: none;
		padding: var(--space-2) .1rem; font-size: var(--text-base); color: var(--ink); min-height: var(--tap-min);
	}
	select:focus { outline: none; border-bottom-color: var(--accent); box-shadow: 0 1px 0 0 var(--accent); }
</style>
