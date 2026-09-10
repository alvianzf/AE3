<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto, invalidateAll } from '$app/navigation';
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

	// specs/v4.1/03 H5 — arriving from "Add as client" on the Contacts page
	// (?prefill_name=&prefill_email=) opens this dialog pre-filled instead
	// of requiring the name/email to be retyped.
	onMount(() => {
		const prefillName = page.url.searchParams.get('prefill_name');
		const prefillEmail = page.url.searchParams.get('prefill_email');
		if (prefillName || prefillEmail) {
			name = prefillName ?? '';
			email = prefillEmail ?? '';
			open = true;
			goto('/practitioner/clients', { replaceState: true, noScroll: true, keepFocus: true });
		}
	});

	let removeOpen = $state(false);
	let removeTarget = $state<{ id: string; name: string } | null>(null);
	let removing = $state(false);

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

	// specs/v4.1/03 M9 — was a native confirm(), the only destructive action
	// in this portal not using the app's own Dialog component.
	async function confirmRemove() {
		if (!removeTarget) return;
		removing = true;
		try {
			await del(fetch, `/me/clients/${removeTarget.id}`);
			toast('Client removed.');
			removeOpen = false;
			removeTarget = null;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			removing = false;
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
			<td><Button variant="text" onclick={() => { removeTarget = { id: c.id as string, name: c.name as string }; removeOpen = true; }}>Remove</Button></td>
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

<Dialog bind:open={removeOpen} title="Remove client">
	<p>Remove {removeTarget?.name}? This cannot be undone.</p>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (removeOpen = false)}>Cancel</Button>
		<Button variant="filled" onclick={confirmRemove} loading={removing}>Remove</Button>
	{/snippet}
</Dialog>
