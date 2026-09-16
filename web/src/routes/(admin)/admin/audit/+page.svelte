<script lang="ts">
	import { get } from '$lib/api';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();

	// GET /api/superadmin/audit-log — the read path for core_store.log(),
	// a real Postgres trail of practitioner/admin-management actions
	// (approvals, plan changes, admin created/role-changed/suspended,
	// questionnaire edits). Superadmin-only, so a plain admin sees only
	// the library trail below (adminLog is null for them — +page.ts
	// catches the 403). Distinct from, and in addition to, the Neo4j
	// library-only trail this page already showed.
	let adminLog = $state(data.adminLog);
	let adminPage = $state(1);
	let adminLoading = $state(false);

	async function loadAdminPage(page: number) {
		adminLoading = true;
		try {
			adminLog = await get(fetch, `/superadmin/audit-log?page=${page}&per_page=50`);
			adminPage = page;
		} catch {
			// Not a superadmin, or the call failed — leave the section hidden.
		} finally {
			adminLoading = false;
		}
	}

	const adminTotalPages = $derived(adminLog ? Math.max(1, Math.ceil(adminLog.total / adminLog.per_page)) : 1);
</script>

<svelte:head><title>Audit history — Admin portal</title></svelte:head>

<!-- Pulled out of "2 · What Clinic knows" on the Knowledge page, where a
     6-row inline preview crowded a narrow rail panel. Full history (up to
     the 100 most recent events GET /api/audit returns) gets its own screen
     instead. -->
<Spotlight title="Audit history">
	<p class="hint">Library-only events — who changed what in the knowledge base, and when. Each Pro practitioner's own patient-vault activity is separate and isn't shown here.</p>

	<DataTable
		columns={[{ key: 'actor', label: 'Who', sortable: true }, { key: 'action', label: 'Action', sortable: true }, { key: 'detail', label: 'Detail' }, { key: 'ts', label: 'When', sortable: true }]}
		rows={data.audit}
		empty="Nothing logged yet."
	>
		{#snippet row(a: any)}
			<td>{a.actor}</td>
			<td><Chip tone="neutral">{a.action}</Chip></td>
			<td>{a.detail ?? ''}</td>
			<td>{(a.ts ?? '').slice(0, 16).replace('T', ' ')}</td>
		{/snippet}
	</DataTable>

	{#if adminLog}
		<h2 class="section-title">Admin actions</h2>
		<p class="hint">Practitioner approvals/suspensions, plan changes, and admin-account management — a separate Postgres trail from the library events above. Superadmin-only.</p>

		<DataTable
			columns={[{ key: 'actor', label: 'Who', sortable: true }, { key: 'action', label: 'Action', sortable: true }, { key: 'detail', label: 'Detail' }, { key: 'ts', label: 'When', sortable: true }]}
			rows={adminLog.events}
			empty="Nothing logged yet."
		>
			{#snippet row(a: any)}
				<td>{a.actor}</td>
				<td><Chip tone="neutral">{a.action}</Chip></td>
				<td>{a.detail ?? ''}</td>
				<td>{(a.ts ?? '').slice(0, 16).replace('T', ' ')}</td>
			{/snippet}
		</DataTable>

		{#if adminTotalPages > 1}
			<div class="pager">
				<Button variant="outlined" onclick={() => loadAdminPage(adminPage - 1)} disabled={adminPage <= 1 || adminLoading}>← Prev</Button>
				<span class="hint">Page {adminPage} of {adminTotalPages} ({adminLog.total} event{adminLog.total === 1 ? '' : 's'})</span>
				<Button variant="outlined" onclick={() => loadAdminPage(adminPage + 1)} disabled={adminPage >= adminTotalPages || adminLoading}>Next →</Button>
			</div>
		{/if}
	{/if}
</Spotlight>

<style>
	.hint { margin-bottom: var(--space-4); }
	.section-title { margin-top: var(--space-6); margin-bottom: var(--space-2); }
	.pager { display: flex; align-items: center; gap: var(--space-3); margin-top: var(--space-4); }
</style>
