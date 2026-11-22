<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import Button from '$lib/components/Button.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Toggle from '$lib/components/Toggle.svelte';

	let { data } = $props();

	// Moved out of admin/users' "Clients" tab (ux-implementation-spec.md#4) —
	// this is a read-only cross-practitioner roster, not account management,
	// so it doesn't belong alongside Practitioners/Admins under "Users".
	let clientQuery = $state(page.url.searchParams.get('q') ?? '');
	const filteredClients = $derived.by(() => {
		const needle = clientQuery.trim().toLowerCase();
		if (!needle) return data.clients;
		return data.clients.filter((c: any) =>
			[c.name, c.email, c.practitioner_name].some((v) => (v ?? '').toLowerCase().includes(needle))
		);
	});

	let confirmingClient = $state<{ practitioner_id: string; id: string; name: string; kind: 'suspend' | 'reactivate' } | null>(null);
	let confirmClientOpen = $state(false);

	function askClientConfirm(c: any, kind: 'suspend' | 'reactivate') {
		confirmingClient = { practitioner_id: c.practitioner_id, id: c.id, name: c.name, kind };
		confirmClientOpen = true;
	}

	async function runClientConfirmed() {
		if (!confirmingClient) return;
		const { practitioner_id, id, kind } = confirmingClient;
		confirmClientOpen = false;
		try {
			await post(fetch, `/admin/clients/${practitioner_id}/${id}/${kind}`);
			toast(kind === 'suspend' ? 'Client suspended.' : 'Client reactivated.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}
</script>

<svelte:head><title>Clients — Admin portal</title></svelte:head>

<div class="pane-row"><div class="detail-pane"><div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="users" size={16} /></span><h1>Clients</h1></div></div>
	<p class="hint">A read-only roster across every Pro practitioner's vault — clients hold no account of their own.</p>
	<div class="toolbar">
		<input
			class="search"
			type="search"
			placeholder="Search name, email, or practitioner…"
			bind:value={clientQuery}
			aria-label="Search clients"
		/>
	</div>
	<DataTable
		columns={[{ key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }, { key: 'practitioner_name', label: 'Practitioner' }, { key: 'active', label: 'Status' }, { key: 'actions', label: '' }]}
		rows={filteredClients}
		empty="No clients yet."
	>
		{#snippet row(c)}
			<td>{c.name}</td>
			<td>{c.email}</td>
			<td>{c.practitioner_name}</td>
			<td><Chip tone={c.active ? 'ok' : 'danger'}>{c.active ? 'active' : 'suspended'}</Chip></td>
			<td class="actions">
				<Toggle
					checked={!!c.active}
					onchange={(next) => askClientConfirm(c, next ? 'reactivate' : 'suspend')}
					label="Active status for {c.name}"
				/>
			</td>
		{/snippet}
	</DataTable>
</div></div>

<Dialog bind:open={confirmClientOpen} title={confirmingClient?.kind === 'suspend' ? 'Suspend client' : 'Reactivate client'}>
	{#if confirmingClient}
		<p>
			{confirmingClient.kind === 'suspend'
				? `Suspend "${confirmingClient.name}"?`
				: `Reactivate "${confirmingClient.name}"?`}
		</p>
	{/if}
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (confirmClientOpen = false)}>Cancel</Button>
		<Button variant="danger" onclick={runClientConfirmed}>{confirmingClient?.kind === 'suspend' ? 'Suspend' : 'Reactivate'}</Button>
	{/snippet}
</Dialog>

<style>
	.toolbar { display: flex; justify-content: flex-end; align-items: center; gap: var(--space-3); margin: var(--space-3) 0; }
	.actions { display: flex; align-items: center; gap: .6rem; }
	.search {
		flex: 1 1 auto; max-width: 20rem; font-size: var(--text-sm); padding: .5rem .2rem;
		border: none; border-bottom: 1px solid var(--line-2); background: none; color: var(--ink);
	}
	.search:focus { outline: none; border-bottom-color: var(--accent); box-shadow: 0 1px 0 0 var(--accent); }
</style>
