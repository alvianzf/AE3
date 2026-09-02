<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	let open = $state(false);
	let title = $state('');
	let questionsText = $state('One question per line.\nWhat brings you here today?');
	let submitting = $state(false);

	async function create(e: Event) {
		e.preventDefault();
		submitting = true;
		const questions = questionsText
			.split('\n')
			.map((l) => l.trim())
			.filter(Boolean)
			.map((prompt) => ({ prompt, input_type: 'text' }));
		try {
			await post(fetch, '/admin/questionnaires', { title, questions });
			toast('Questionnaire created.');
			open = false;
			title = '';
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
		<Button variant="filled" onclick={() => (open = true)}>New questionnaire</Button>
	{/snippet}
	<DataTable
		columns={[{ key: 'title', label: 'Title', sortable: true }, { key: 'version', label: 'Version' }, { key: 'is_active', label: 'Active' }]}
		rows={data.questionnaires}
		empty="No questionnaires yet."
	>
		{#snippet row(q)}
			<td>{q.title}</td>
			<td>{q.version}</td>
			<td>{q.is_active ? 'Yes' : 'No'}</td>
		{/snippet}
	</DataTable>
</Spotlight>

<Dialog bind:open title="New questionnaire">
	<form onsubmit={create} id="qn-form">
		<TextField label="Title" bind:value={title} required />
		<TextField label="Questions" type="textarea" bind:value={questionsText} hint="One question per line." />
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
		<Button type="submit" onclick={create} loading={submitting}>Create</Button>
	{/snippet}
</Dialog>
