<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();

	async function setStatus(id: string, status: string) {
		try {
			await api(fetch, `/me/contacts/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) });
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}
</script>

<svelte:head><title>Contacts — Practitioner portal</title></svelte:head>

<Spotlight title="Contact submissions">
	<DataTable
		columns={[{ key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }, { key: 'message', label: 'Message' }, { key: 'status', label: 'Status' }, { key: 'actions', label: '' }]}
		rows={data.contacts}
		empty="No contact submissions."
	>
		{#snippet row(c)}
			<td>{c.name}</td>
			<td>{c.email}</td>
			<td class="msg">{c.message}</td>
			<td><Chip tone={c.status === 'new' ? 'accent' : 'neutral'}>{c.status}</Chip></td>
			<td>
				{#if c.status === 'new'}
					<Button variant="text" onclick={() => setStatus(c.id as string, 'handled')}>Mark handled</Button>
				{/if}
			</td>
		{/snippet}
	</DataTable>
</Spotlight>

<style>
	.msg { max-width: 22rem; white-space: normal; }
</style>
