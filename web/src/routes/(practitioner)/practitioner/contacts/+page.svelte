<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { api } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Button from '$lib/components/Button.svelte';
	import Icon from '$lib/components/Icon.svelte';

	// specs/v4.1/03 H5 — converting a contact into a client used to mean
	// retyping the name/email it already contains into a separate dialog.
	// Also marks the submission "contacted" — converting someone to a
	// client IS the resolution, not a separate step a practitioner has to
	// remember to do afterward.
	function addAsClient(c: any) {
		setStatus(c.id, 'contacted', { silent: true });
		goto(`/practitioner/clients?prefill_name=${encodeURIComponent(c.name)}&prefill_email=${encodeURIComponent(c.email)}`);
	}

	function mailtoLink(c: any) {
		const subject = encodeURIComponent('Re: your message');
		const body = encodeURIComponent(`Hi ${c.name},\n\n`);
		return `mailto:${c.email}?subject=${subject}&body=${body}`;
	}

	let { data } = $props();

	// Found live, 2026-11-26: this sent status:"handled", a value the
	// backend has never accepted (core_store.update_contact_status only
	// allows new/contacted/closed) — every click of what used to be "Mark
	// handled" silently 400'd, so a submission could never actually be
	// cleared. That's the "no apparent flow" complaint: the one action
	// meant to resolve a message never worked, so the list only ever grew.
	async function setStatus(id: string, status: 'contacted' | 'closed', opts?: { silent?: boolean }) {
		try {
			await api(fetch, `/me/contacts/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) });
			await invalidateAll();
		} catch (err: any) {
			if (!opts?.silent) toast(err.message, 'alert');
		}
	}

	const STATUS_LABELS: Record<string, string> = { new: 'New', contacted: 'Contacted', closed: 'Closed' };
</script>

<svelte:head><title>Contacts — Practitioner portal</title></svelte:head>

<div class="pane-row"><div class="detail-pane"><div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="mail" size={16} /></span><h1>Contact submissions</h1></div></div>
	<p class="hint">Messages sent through your public profile's contact form. Reply by email, then mark it contacted — or turn them into a client directly.</p>
	<DataTable
		columns={[{ key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }, { key: 'message', label: 'Message' }, { key: 'status', label: 'Status' }, { key: 'actions', label: '' }]}
		rows={data.contacts}
		empty="No contact submissions yet — they'll show up here when someone messages you through your public profile."
	>
		{#snippet row(c)}
			<td>{c.name}</td>
			<td><a href={mailtoLink(c)}>{c.email}</a></td>
			<td class="msg">{c.message}</td>
			<td><Chip tone={c.status === 'new' ? 'accent' : 'neutral'}>{STATUS_LABELS[c.status as string] ?? c.status}</Chip></td>
			<td class="actions">
				<Button variant="text" href={mailtoLink(c)}><Icon name="mail" size={15} />Reply by email</Button>
				<Button variant="text" onclick={() => addAsClient(c)}><Icon name="plus" size={15} />Add as client</Button>
				{#if c.status === 'new'}
					<Button variant="text" onclick={() => setStatus(c.id as string, 'contacted')}><Icon name="check" size={15} />Mark contacted</Button>
				{/if}
			</td>
		{/snippet}
	</DataTable>
</div></div>

<style>
	.msg { max-width: 22rem; white-space: normal; }
	.actions { display: flex; gap: var(--space-2); white-space: nowrap; }
</style>
