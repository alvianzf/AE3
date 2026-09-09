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
	let questionsText = $state('One question per line.\nWhat brings you here today?');
	let submitting = $state(false);

	function openCreate() {
		editingId = null;
		title = '';
		questionsText = 'One question per line.\nWhat brings you here today?';
		open = true;
	}

	async function openEdit(id: string) {
		try {
			const q = await get(fetch, `/admin/questionnaires/${id}`);
			editingId = id;
			title = q.title;
			// The per-question type/theme/options a full builder would carry
			// (specs/v4/04-known-issues.md#m5) is out of scope here, matching
			// this same one-line-per-question approach "New questionnaire"
			// already uses — editing is lossy for anything beyond the prompt
			// text of a plain "text" question, which is what this page can
			// create in the first place.
			questionsText = (q.questions ?? []).map((qq: any) => qq.prompt).join('\n');
			open = true;
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function save(e: Event) {
		e.preventDefault();
		submitting = true;
		const questions = questionsText
			.split('\n')
			.map((l) => l.trim())
			.filter(Boolean)
			.map((prompt) => ({ prompt, input_type: 'text' }));
		try {
			await post(fetch, editingId ? `/admin/questionnaires/${editingId}` : '/admin/questionnaires', { title, questions });
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

<Dialog bind:open title={editingId ? 'Edit questionnaire' : 'New questionnaire'}>
	<form onsubmit={save} id="qn-form">
		<TextField label="Title" bind:value={title} required />
		<TextField label="Questions" type="textarea" bind:value={questionsText} hint="One question per line." />
		{#if editingId}
			<p class="hint">Saving creates a new version and makes it the active questionnaire — clients will answer this one from now on.</p>
		{/if}
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
		<Button type="submit" onclick={save} loading={submitting}>{editingId ? 'Save new version' : 'Create'}</Button>
	{/snippet}
</Dialog>

<style>
	.edit {
		font: inherit; font-size: var(--text-sm); font-weight: 650; cursor: pointer;
		border: 1px solid var(--line); background: var(--panel); color: var(--accent-ink);
		border-radius: var(--r); padding: .3rem .7rem;
	}
	.edit:hover { border-color: var(--accent); background: var(--accent-soft); }
</style>
