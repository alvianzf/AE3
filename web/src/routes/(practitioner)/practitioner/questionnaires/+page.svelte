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

	// Mirrors the admin builder (../../../(admin)/admin/questionnaires) —
	// same core_store.QUESTION_TYPES, same question editor — but scoped to
	// this practitioner's own questionnaires via /api/me/questionnaires*
	// instead of /api/admin/questionnaires*. Only a Pro practitioner ever
	// has clients to send one to (require_pro_practitioner).
	// "info" (plain instructional text, no answer) and "repeater" (an
	// addable table, or a fixed grid when it has row labels) are Client
	// Intake Links additions — core_store.QUESTION_TYPES.
	const QUESTION_TYPES = ['text', 'number', 'date', 'choice', 'multi_choice', 'info', 'repeater'] as const;
	const MAPS_TO_FIELDS = ['', 'client_name', 'client_email', 'client_dob', 'client_country'] as const;

	type Question = {
		key: string; // local-only, for #each keying
		prompt: string;
		input_type: (typeof QUESTION_TYPES)[number];
		options: string; // comma-separated in the UI, split to an array on save
		theme: string;
		allowOther: boolean;
		columns: string; // repeater: comma-separated column names
		fixedRows: string; // repeater: comma-separated row labels, empty = addable table
		mapsTo: string; // only meaningful on an 'initial'-kind questionnaire
	};

	let { data } = $props();
	let open = $state(false);
	let linkOpen = $state(false);
	let linkFor = $state<any>(null);
	let linkClientId = $state('');
	let linkUrl = $state('');
	let linkCreating = $state(false);
	// qKind toggles what submitting a link for THIS questionnaire does —
	// see app/core_store.py's QUESTIONNAIRE_KINDS.
	let qKind = $state<'initial' | 'followup'>('followup');
	// Set when editing an existing questionnaire; null means "New
	// questionnaire". Editing always creates a new version rather than
	// mutating in place (core_store.edit_questionnaire) — the new version
	// keeps the version it replaces' active state untouched, since
	// activation is now a separate explicit action.
	let editingId = $state<string | null>(null);
	// A practitioner can see the site default (GET /api/me/questionnaires
	// now includes it, per direct request) but never modify it — edit/
	// activate/deactivate all 404 on it server-side regardless, this just
	// keeps the UI from offering actions that would fail.
	let viewOnly = $state(false);
	let title = $state('');
	let questions = $state<Question[]>([]);
	let submitting = $state(false);

	function isMine(q: any) {
		return q.practitioner_id != null;
	}

	function blankQuestion(): Question {
		return {
			key: crypto.randomUUID(), prompt: '', input_type: 'text', options: '', theme: 'General',
			allowOther: false, columns: '', fixedRows: '', mapsTo: ''
		};
	}

	function mappedQuestion(prompt: string, mapsTo: string, inputType: Question['input_type'] = 'text'): Question {
		return { ...blankQuestion(), prompt, input_type: inputType, mapsTo };
	}

	// An 'initial' questionnaire needs exactly one client_name and one
	// client_email question before it can even save — rather than make a
	// practitioner discover that by hitting the save error, pre-fill the
	// four client fields (still fully editable/removable) the moment they
	// switch to this kind, same as a real intake form would start. Only
	// when nothing's mapped yet — switching back and forth, or opening an
	// existing questionnaire that already has its own mapped questions,
	// must never clobber real content.
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
		viewOnly = false;
		title = '';
		qKind = 'followup';
		questions = [blankQuestion()];
		open = true;
	}

	async function openEdit(q: any) {
		viewOnly = !isMine(q);
		try {
			const full = await get(fetch, `/me/questionnaires/${q.id}`);
			editingId = full.id;
			title = full.title;
			qKind = full.kind === 'initial' ? 'initial' : 'followup';
			questions = (full.questions ?? []).map((qq: any) => ({
				key: crypto.randomUUID(),
				prompt: qq.prompt,
				input_type: qq.input_type ?? 'text',
				options: (qq.options ?? []).join(', '),
				theme: qq.theme || 'General',
				allowOther: !!qq.allow_other,
				columns: (qq.columns ?? []).join(', '),
				fixedRows: (qq.fixed_rows ?? []).join(', '),
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
				allow_other: (q.input_type === 'choice' || q.input_type === 'multi_choice') && q.allowOther,
				columns: q.input_type === 'repeater' ? q.columns.split(',').map((c) => c.trim()).filter(Boolean) : [],
				fixed_rows:
					q.input_type === 'repeater' && q.fixedRows.trim()
						? q.fixedRows.split(',').map((r) => r.trim()).filter(Boolean)
						: null,
				maps_to: qKind === 'initial' && q.mapsTo ? q.mapsTo : null
			}));
		try {
			await post(fetch, editingId ? `/me/questionnaires/${editingId}/edit` : '/me/questionnaires', {
				title,
				kind: qKind,
				questions: payload
			});
			toast(editingId ? 'New version saved.' : 'Questionnaire created.');
			open = false;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}

	function openLink(q: any) {
		linkFor = q;
		linkClientId = '';
		linkUrl = '';
		linkOpen = true;
	}

	async function createLink() {
		linkCreating = true;
		try {
			const result = await post(fetch, `/me/questionnaires/${linkFor.id}/links`, {
				client_id: linkFor.kind === 'initial' ? null : linkClientId || null
			});
			linkUrl = `${window.location.origin}${result.url}`;
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			linkCreating = false;
		}
	}

	async function copyLink() {
		await navigator.clipboard.writeText(linkUrl);
		toast('Link copied.');
	}

	async function setActive(id: string, active: boolean) {
		try {
			await post(fetch, `/me/questionnaires/${id}/${active ? 'activate' : 'deactivate'}`);
			toast(active ? 'Questionnaire activated.' : 'Questionnaire deactivated.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}
</script>

<svelte:head><title>Questionnaires — Practitioner portal</title></svelte:head>

<div class="pane-row"><div class="detail-pane"><div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="clipboard" size={16} /></span><h1>Questionnaires</h1></div><div class="head-actions">{@render actions()}</div></div>
	{#snippet actions()}
		<Button variant="filled" onclick={openCreate}><Icon name="plus" size={15} />New questionnaire</Button>
	{/snippet}
	<p class="hint">
		Your active questionnaire goes to your own clients instead of the site default. Deactivate
		it any time to fall back to the default.
	</p>
	<DataTable
		columns={[{ key: 'title', label: 'Title', sortable: true }, { key: 'owner', label: 'Owner' }, { key: 'kind', label: 'Kind' }, { key: 'version', label: 'Version' }, { key: 'is_active', label: 'Active' }, { key: 'actions', label: '' }]}
		rows={data.questionnaires}
		empty="You haven't created a questionnaire yet — your clients see the site default until you do."
	>
		{#snippet row(q: any)}
			<td>{q.title}</td>
			<td>{isMine(q) ? 'Yours' : 'Site default'}</td>
			<td>{q.kind === 'initial' ? 'New client' : 'Follow-up'}</td>
			<td>{q.version}</td>
			<td>{#if q.is_active}<Chip tone="ok">Active</Chip>{:else}No{/if}</td>
			<td class="actions">
				{#if isMine(q)}
					<button class="edit" onclick={() => openEdit(q)}><Icon name="edit" size={14} />Edit</button>
					<button class="edit" onclick={() => openLink(q)}><Icon name="send" size={14} />Get link</button>
					{#if q.is_active}
						<Button variant="text" onclick={() => setActive(q.id, false)}><Icon name="pause" size={15} />Deactivate</Button>
					{:else}
						<Button variant="text" onclick={() => setActive(q.id, true)}><Icon name="play" size={15} />Activate</Button>
					{/if}
				{:else}
					<button class="edit" onclick={() => openEdit(q)}><Icon name="eye" size={14} />View</button>
				{/if}
			</td>
		{/snippet}
	</DataTable>
</div></div>

<Dialog bind:open title={viewOnly ? title : editingId ? 'Edit questionnaire' : 'New questionnaire'} wide>
	{#if viewOnly}
		<p class="hint">The site default — read-only. Create your own above to override it for your clients.</p>
	{/if}
	<form onsubmit={save} id="qn-form" inert={viewOnly}>
		<TextField label="Title" bind:value={title} required disabled={viewOnly} />

		<div class="field">
			<label for="qn-kind">Who answers this, via a link</label>
			<select id="qn-kind" bind:value={qKind} disabled={viewOnly} onchange={onKindChange}>
				<option value="followup">An existing client (follow-up)</option>
				<option value="initial">Someone with no client record yet (new intake)</option>
			</select>
		</div>
		{#if qKind === 'initial'}
			<p class="hint">Mark one question "Maps to → Client name" and one "Maps to → Client email" below — submitting the link creates the client record from those two answers.</p>
		{/if}

		<div class="questions">
			{#each questions as q, i (q.key)}
				<div class="question-row">
					<div class="question-head">
						<span class="num">{i + 1}</span>
						{#if !viewOnly}
							<button type="button" class="remove" onclick={() => removeQuestion(q.key)} disabled={questions.length === 1} aria-label="Remove question">&times;</button>
						{/if}
					</div>
					<TextField label="Prompt" bind:value={q.prompt} required disabled={viewOnly} />
					<div class="question-fields">
						<div class="field">
							<label for="type-{q.key}">Type</label>
							<select id="type-{q.key}" bind:value={q.input_type} disabled={viewOnly}>
								{#each QUESTION_TYPES as t (t)}
									<option value={t}>{t.replaceAll('_', ' ')}</option>
								{/each}
							</select>
						</div>
						<TextField label="Theme" bind:value={q.theme} hint="Groups questions on the client's page." disabled={viewOnly} />
					</div>
					{#if q.input_type === 'choice' || q.input_type === 'multi_choice'}
						<TextField label="Options" bind:value={q.options} hint="Comma-separated, e.g. Never, Sometimes, Often" disabled={viewOnly} />
						<label class="checkbox-row">
							<input type="checkbox" bind:checked={q.allowOther} disabled={viewOnly} />
							Add an "Other, please specify" option
						</label>
					{:else if q.input_type === 'repeater'}
						<TextField label="Columns" bind:value={q.columns} hint="Comma-separated, e.g. Medication, Dose, How often, Reason" disabled={viewOnly} />
						<TextField label="Fixed row labels (optional)" bind:value={q.fixedRows} hint="Leave blank for an addable table (e.g. Medications). Fill in for a fixed grid (e.g. Breakfast, Lunch, Dinner)." disabled={viewOnly} />
					{/if}
					{#if qKind === 'initial' && q.input_type !== 'info' && q.input_type !== 'repeater'}
						<div class="field">
							<label for="maps-{q.key}">Maps to (new-client field)</label>
							<select id="maps-{q.key}" bind:value={q.mapsTo} disabled={viewOnly}>
								{#each MAPS_TO_FIELDS as f (f)}
									<option value={f}>{f ? f.replace('client_', 'Client ') : '— none —'}</option>
								{/each}
							</select>
						</div>
					{/if}
				</div>
			{/each}
		</div>
		{#if !viewOnly}
			<Button type="button" variant="outlined" onclick={addQuestion}>+ Add question</Button>
		{/if}

		{#if editingId && !viewOnly}
			<p class="hint">Saving creates a new version. Activate it from the list once you're ready for clients to see it.</p>
		{/if}
	</form>
	{#snippet footer()}
		{#if viewOnly}
			<Button variant="ghost" onclick={() => (open = false)}>Close</Button>
		{:else}
			<Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
			<Button onclick={save} loading={submitting}>{editingId ? 'Save new version' : 'Create'}</Button>
		{/if}
	{/snippet}
</Dialog>

<Dialog bind:open={linkOpen} title="Get link — {linkFor?.title ?? ''}">
	{#if linkFor?.kind === 'followup'}
		<div class="field">
			<label for="link-client">Client</label>
			<select id="link-client" bind:value={linkClientId}>
				<option value="">Choose a client…</option>
				{#each data.clients as c (c.id)}<option value={c.id}>{c.name}</option>{/each}
			</select>
		</div>
	{:else}
		<p class="hint">This is a "new intake" questionnaire — the link isn't tied to any existing client. Submitting it creates one.</p>
	{/if}
	{#if linkUrl}
		<div class="link-row">
			<TextField label="Link" value={linkUrl} disabled />
			<Button variant="outlined" onclick={copyLink}>Copy</Button>
		</div>
		<p class="hint">Stays valid across visits — only invalidated once it's submitted.</p>
	{/if}
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (linkOpen = false)}>Close</Button>
		<Button
			onclick={createLink} loading={linkCreating}
			disabled={linkFor?.kind === 'followup' && !linkClientId}
		>Generate link</Button>
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
	.checkbox-row { display: flex; align-items: center; gap: .5rem; font-size: var(--text-sm); }
	.link-row { display: flex; align-items: flex-end; gap: var(--space-3); }
	.link-row :global(.field) { flex: 1; }
</style>
