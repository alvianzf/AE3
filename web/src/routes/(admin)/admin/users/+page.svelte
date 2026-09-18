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
	import Icon from '$lib/components/Icon.svelte';
	import Toggle from '$lib/components/Toggle.svelte';

	let { data } = $props();
	let active = $state('practitioners');
	let openNew = $state(false);
	// Admin-account management (create/role-change/suspend) is
	// superadmin-only on the backend (auth.require_superadmin) — a plain
	// admin can reach this tab (the layout guard only checks role==='admin')
	// so the controls themselves must be gated too, or a non-superadmin
	// sees fully-interactive buttons that 403 on every click.
	const isSuperadmin = $derived(data.session?.admin_role === 'superadmin');

	// Practitioner search — same client-side-filter-over-an-already-loaded
	// list approach the Library page's search box uses.
	let practitionerQuery = $state('');
	const filteredPractitioners = $derived.by(() => {
		const needle = practitionerQuery.trim().toLowerCase();
		if (!needle) return data.practitioners;
		return data.practitioners.filter((p: any) =>
			[p.name, p.email].some((v) => (v ?? '').toLowerCase().includes(needle))
		);
	});

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let submitting = $state(false);

	// --- Admins tab: mirrors the Practitioners tab's create/confirm/toast
	// pattern above, wired to the four superadmin routes that already
	// existed on the backend with no UI (app/main.py:1115-1156).
	let openNewAdmin = $state(false);
	let adminName = $state('');
	let adminEmail = $state('');
	let adminPassword = $state('');
	let adminRole = $state('admin');
	let submittingAdmin = $state(false);

	async function createAdmin(e: Event) {
		e.preventDefault();
		submittingAdmin = true;
		try {
			await post(fetch, '/superadmin/admins', {
				name: adminName, email: adminEmail, password: adminPassword, role: adminRole
			});
			toast('Admin created.');
			openNewAdmin = false;
			adminName = adminEmail = adminPassword = '';
			adminRole = 'admin';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submittingAdmin = false;
		}
	}

	async function setAdminRole(id: string, role: string) {
		try {
			await put(fetch, `/superadmin/admins/${id}/role`, { role });
			toast('Role updated.');
			await invalidateAll();
		} catch (err: any) {
			// The backend refuses to demote the last active superadmin (400) —
			// surface that message rather than swallowing it.
			toast(err.message, 'alert');
			await invalidateAll();
		}
	}

	let confirmingAdmin = $state<{ id: string; name: string; kind: 'suspend' | 'reactivate' } | null>(null);
	let confirmAdminOpen = $state(false);

	function askAdminConfirm(id: string, name: string, kind: 'suspend' | 'reactivate') {
		confirmingAdmin = { id, name, kind };
		confirmAdminOpen = true;
	}

	async function runAdminConfirmed() {
		if (!confirmingAdmin) return;
		const { id, kind } = confirmingAdmin;
		confirmAdminOpen = false;
		try {
			await post(fetch, `/superadmin/admins/${id}/${kind}`);
			toast(kind === 'suspend' ? 'Admin suspended.' : 'Admin reactivated.');
			await invalidateAll();
		} catch (err: any) {
			// Same last-active-superadmin guardrail as setAdminRole above.
			toast(err.message, 'alert');
		}
	}

	// --- Clients tab: read-only listing across every Pro practitioner's
	// vault, plus a suspend/reactivate action (app/vault.py's new `active`
	// column — the same pattern as practitioner/admin suspension, not a
	// separate mechanism).
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

	async function approve(id: string) {
		try { await post(fetch, `/admin/practitioners/${id}/approve`); await invalidateAll(); }
		catch (err: any) { toast(err.message, 'alert'); }
	}

	// Suspend and Reject are equally consequential (both block a
	// practitioner's access), but previously used two different
	// confirmation patterns — a native confirm() for Suspend, none at all
	// for Reject (specs/v4/04-known-issues.md#l3). One shared dialog now
	// covers both, using the app's own Dialog like everywhere else already
	// does.
	let confirming = $state<{ id: string; name: string; kind: 'suspend' | 'reject' } | null>(null);
	let confirmOpen = $state(false);

	function askConfirm(id: string, name: string, kind: 'suspend' | 'reject') {
		confirming = { id, name, kind };
		confirmOpen = true;
	}

	async function runConfirmed() {
		if (!confirming) return;
		const { id, kind } = confirming;
		confirmOpen = false;
		try {
			await post(fetch, `/admin/practitioners/${id}/${kind}`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}
	async function setPlan(id: string, plan: string) {
		try { await put(fetch, `/admin/practitioners/${id}/plan`, { plan }); toast('Plan updated.'); await invalidateAll(); }
		catch (err: any) { toast(err.message, 'alert'); }
	}
	// Library upload is an explicit per-practitioner grant, not a plan perk
	// (a superadmin/admin decides WHICH practitioners get it) — separate
	// toggle from the Basic/Pro plan select above.
	async function setCanUploadLibrary(id: string, allowed: boolean) {
		try {
			await post(fetch, `/admin/practitioners/${id}/can-upload-library`, { allowed });
			toast(allowed ? 'Library upload allowed.' : 'Library upload revoked.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
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
	<Tabs bind:active tabs={[{ id: 'practitioners', label: 'Practitioners' }, { id: 'admins', label: 'Admins' }, { id: 'clients', label: 'Clients' }]} />

	{#if active === 'practitioners'}
		<div class="toolbar">
			<input
				class="search"
				type="search"
				placeholder="Search name or email…"
				bind:value={practitionerQuery}
				aria-label="Search practitioners"
			/>
			<Button variant="filled" onclick={() => (openNew = true)}><Icon name="plus" size={15} />New practitioner</Button>
		</div>
		<DataTable
			columns={[{ key: 'name', label: 'Name', sortable: true }, { key: 'email', label: 'Email' }, { key: 'status', label: 'Status' }, { key: 'plan', label: 'Plan' }, { key: 'clients', label: 'Clients' }, { key: 'actions', label: '' }]}
			rows={filteredPractitioners}
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
				<td>{p.clients ?? '—'}</td>
				<td class="actions">
					{#if p.status === 'pending'}
						<Button variant="text" onclick={() => approve(p.id as string)}><Icon name="check" size={15} />Approve</Button>
						<Button variant="text" onclick={() => askConfirm(p.id as string, p.name as string, 'reject')}><Icon name="x" size={15} />Reject</Button>
					{:else}
						<Toggle
							checked={p.status === 'approved'}
							onchange={(next) => (next ? approve(p.id as string) : askConfirm(p.id as string, p.name as string, 'suspend'))}
							label="Approved status for {p.name}"
						/>
					{/if}
					<span class="toggle-row">
						<Toggle
							checked={!!p.can_upload_library}
							onchange={(next) => setCanUploadLibrary(p.id as string, next)}
							label="Library upload for {p.name}"
						/>
						<span class="hint">Library upload</span>
					</span>
				</td>
			{/snippet}
		</DataTable>
	{:else if active === 'admins'}
		{#if isSuperadmin}
			<div class="toolbar">
				<Button variant="filled" onclick={() => (openNewAdmin = true)}><Icon name="plus" size={15} />New admin</Button>
			</div>
		{/if}
		<DataTable
			columns={[{ key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }, { key: 'role', label: 'Role' }, { key: 'is_active', label: 'Status' }, { key: 'actions', label: '' }]}
			rows={data.admins}
			empty="No admins yet."
		>
			{#snippet row(a)}
				<td>{a.name}</td>
				<td>{a.email}</td>
				<td>
					{#if isSuperadmin}
						<select value={a.role} onchange={(e) => setAdminRole(a.id as string, (e.target as HTMLSelectElement).value)}>
							<option value="admin">Admin</option>
							<option value="superadmin">Superadmin</option>
						</select>
					{:else}
						{a.role}
					{/if}
				</td>
				<td><Chip tone={a.is_active ? 'ok' : 'danger'}>{a.is_active ? 'active' : 'suspended'}</Chip></td>
				<td class="actions">
					{#if isSuperadmin}
						<Toggle
							checked={!!a.is_active}
							onchange={(next) => askAdminConfirm(a.id as string, a.name as string, next ? 'reactivate' : 'suspend')}
							label="Active status for {a.name}"
						/>
					{/if}
				</td>
			{/snippet}
		</DataTable>
	{:else}
		<DataTable
			columns={[{ key: 'name', label: 'Name' }, { key: 'email', label: 'Email' }, { key: 'practitioner_name', label: 'Practitioner' }, { key: 'active', label: 'Status' }, { key: 'actions', label: '' }]}
			rows={data.clients}
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
		<Button onclick={createPractitioner} loading={submitting}>Create</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={confirmOpen} title={confirming?.kind === 'suspend' ? 'Suspend practitioner' : 'Reject application'}>
	{#if confirming}
		<p>
			{confirming.kind === 'suspend'
				? `Suspend "${confirming.name}"? They will immediately lose portal access.`
				: `Reject "${confirming.name}"'s application?`}
		</p>
	{/if}
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (confirmOpen = false)}>Cancel</Button>
		<Button variant="danger" onclick={runConfirmed}>{confirming?.kind === 'suspend' ? 'Suspend' : 'Reject'}</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={openNewAdmin} title="New admin">
	<form onsubmit={createAdmin} id="na-form">
		<TextField label="Name" bind:value={adminName} required />
		<TextField label="Email" type="email" bind:value={adminEmail} required />
		<TextField label="Temporary password" type="password" bind:value={adminPassword} required />
		<div class="field">
			<label for="na-role">Role</label>
			<select id="na-role" bind:value={adminRole}>
				<option value="admin">Admin</option>
				<option value="superadmin">Superadmin</option>
			</select>
		</div>
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (openNewAdmin = false)}>Cancel</Button>
		<Button onclick={createAdmin} loading={submittingAdmin}>Create</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={confirmAdminOpen} title={confirmingAdmin?.kind === 'suspend' ? 'Suspend admin' : 'Reactivate admin'}>
	{#if confirmingAdmin}
		<p>
			{confirmingAdmin.kind === 'suspend'
				? `Suspend "${confirmingAdmin.name}"? They will immediately lose portal access.`
				: `Reactivate "${confirmingAdmin.name}"?`}
		</p>
	{/if}
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (confirmAdminOpen = false)}>Cancel</Button>
		<Button variant="danger" onclick={runAdminConfirmed}>{confirmingAdmin?.kind === 'suspend' ? 'Suspend' : 'Reactivate'}</Button>
	{/snippet}
</Dialog>

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
	.toggle-row { display: inline-flex; align-items: center; gap: .5rem; }
	select { border: 1px solid var(--line-2); border-radius: var(--r); padding: .3rem .5rem; }
	.field { display: flex; flex-direction: column; gap: .35rem; }
	.search {
		flex: 1 1 auto; max-width: 20rem; font-size: var(--text-sm); padding: .5rem .8rem;
		border: 1px solid var(--line-2); border-radius: var(--r); background: var(--panel); color: var(--ink);
	}
	.search:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
</style>
