<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { post, del } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Button from '$lib/components/Button.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import TextField from '$lib/components/TextField.svelte';

	let { data } = $props();
	let open = $state(false);
	let name = $state('');
	let email = $state('');
	let dob = $state('');
	let country = $state('');
	let submitting = $state(false);

	async function create(e: Event) {
		e.preventDefault();
		submitting = true;
		try {
			await post(fetch, '/me/clients', { name, email, dob: dob || null, country: country || null });
			toast('Client added.');
			open = false;
			name = email = dob = country = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}

	async function remove(id: string) {
		if (!confirm('Remove this client? This cannot be undone.')) return;
		try {
			await del(fetch, `/me/clients/${id}`);
			toast('Client removed.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}
</script>

<svelte:head><title>Clients — Practitioner portal</title></svelte:head>

<Spotlight title="Clients">
	{#snippet actions()}
		<Button variant="filled" onclick={() => (open = true)}>Add client</Button>
	{/snippet}
	<DataTable
		columns={[{ key: 'name', label: 'Name', sortable: true }, { key: 'email', label: 'Email', sortable: true }, { key: 'country', label: 'Country' }, { key: 'actions', label: '' }]}
		rows={data.clients}
		empty="No clients yet — add your first one."
	>
		{#snippet row(c)}
			<td><a href="/practitioner/clients/{c.id}">{c.name}</a></td>
			<td>{c.email}</td>
			<td>{c.country ?? ''}</td>
			<td><Button variant="text" onclick={() => remove(c.id as string)}>Remove</Button></td>
		{/snippet}
	</DataTable>
</Spotlight>

<Dialog bind:open title="Add a client">
	<form onsubmit={create} id="add-client-form">
		<TextField label="Name" bind:value={name} required />
		<TextField label="Email" type="email" bind:value={email} required />
		<TextField label="Date of birth" type="date" bind:value={dob} />
		<TextField label="Country" bind:value={country} />
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
		<Button type="submit" onclick={create} loading={submitting}>Add client</Button>
	{/snippet}
</Dialog>
