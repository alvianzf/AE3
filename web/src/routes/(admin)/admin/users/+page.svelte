<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { post, put } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Quiet from '$lib/components/Quiet.svelte';
	import Tabs from '$lib/components/Tabs.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Button from '$lib/components/Button.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import TextField from '$lib/components/TextField.svelte';

	let { data } = $props();
	let active = $state('practitioners');
	let openNew = $state(false);

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let submitting = $state(false);

	async function approve(id: string) {
		try { await post(fetch, `/admin/practitioners/${id}/approve`); await invalidateAll(); }
		catch (err: any) { toast(err.message, 'alert'); }
	}
	async function reject(id: string) {
		try { await post(fetch, `/admin/practitioners/${id}/reject`); await invalidateAll(); }
		catch (err: any) { toast(err.message, 'alert'); }
	}
	async function suspend(id: string) {
		if (!confirm('Suspend this practitioner?')) return;
		try { await post(fetch, `/admin/practitioners/${id}/suspend`); await invalidateAll(); }
		catch (err: any) { toast(err.message, 'alert'); }
	}
	async function setPlan(id: string, plan: string) {
		try { await put(fetch, `/admin/practitioners/${id}/plan`, { plan }); toast('Plan updated.'); await invalidateAll(); }
		catch (err: any) { toast(err.message, 'alert'); }
	}
	async function createPractitioner(e: Event) {
		e.preventDefault();
		submitting = true;
		try {
			await post(fetch, '/admin/practitioners', { name, email, password });
			toast('Practitioner created.');
			openNew = false;
			name = email = password = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Users — Admin portal</title></svelte:head>

<!-- specs/v4/03: Tier 2 on this screen — a datatable an admin revisits many
     times a day doesn't need the red band's attention-getting weight. -->
<Quiet title="Users">
	<Tabs bind:active tabs={[{ id: 'practitioners', label: 'Practitioners' }, { id: 'admins', label: 'Admins' }]} />

	{#if active === 'practitioners'}
		<div class="toolbar">
			<Button variant="filled" onclick={() => (openNew = true)}>New practitioner</Button>
		</div>
		<DataTable
			columns={[{ key: 'name', label: 'Name', sortable: true }, { key: 'email', label: 'Email' }, { key: 'status', label: 'Status' }, { key: 'plan', label: 'Plan' }, { key: 'actions', label: '' }]}
			rows={data.practitioners}
			empty="No practitioners yet."
		>
			{#snippet row(p)}
				<td>{p.name}</td>
				<td>{p.email}</td>
				<td><Chip tone={p.status === 'approved' ? 'ok' : p.status === 'pending' ? 'warn' : 'danger'}>{p.status}</Chip></td>
				<td>
					<select value={p.plan} onchange={(e) => setPlan(p.id as string, (e.target as HTMLSelectElement).value)}>
						<option value="basic">Basic</option>
						<option value="pro">Pro</option>
					</select>
				</td>
				<td class="actions">
					{#if p.status === 'pending'}
						<Button variant="text" onclick={() => approve(p.id as string)}>Approve</Button>
						<Button variant="text" onclick={() => reject(p.id as string)}>Reject</Button>
					{:else if p.status === 'approved'}
						<Button variant="text" onclick={() => suspend(p.id as string)}>Suspend</Button>
					{/if}
				</td>
			{/snippet}
		</DataTable>
	{:else}
		<DataTable
			columns={[{ key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }, { key: 'role', label: 'Role' }]}
			rows={data.admins}
			empty="No admins yet."
		>
			{#snippet row(a)}
				<td>{a.name}</td>
				<td>{a.email}</td>
				<td><Chip tone="neutral">{a.role}</Chip></td>
			{/snippet}
		</DataTable>
	{/if}
</Quiet>

<Dialog bind:open={openNew} title="New practitioner">
	<form onsubmit={createPractitioner} id="np-form">
		<TextField label="Name" bind:value={name} required />
		<TextField label="Email" type="email" bind:value={email} required />
		<TextField label="Temporary password" type="password" bind:value={password} required />
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (openNew = false)}>Cancel</Button>
		<Button type="submit" onclick={createPractitioner} loading={submitting}>Create</Button>
	{/snippet}
</Dialog>

<style>
	.toolbar { display: flex; justify-content: flex-end; margin: var(--space-3) 0; }
	.actions { display: flex; gap: .25rem; }
	select { border: 1px solid var(--line-2); border-radius: var(--r); padding: .3rem .5rem; }
</style>
