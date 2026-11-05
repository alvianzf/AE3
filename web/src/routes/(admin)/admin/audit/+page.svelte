<script lang="ts">
	import { get } from '$lib/api';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Button from '$lib/components/Button.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Tabs from '$lib/components/Tabs.svelte';

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

	// Two genuinely separate trails (library events vs. admin-account
	// actions, neither endpoint shares a store or a schema) now live as
	// tabs instead of two full tables stacked on one scroll — the second
	// one only exists at all for a superadmin, so the tab itself is
	// conditional on that rather than always showing an empty-looking
	// second table.
	let active = $state('library');

	// Both endpoints return up to a fixed window (100 most recent for
	// library, one page of 50 for admin actions) with no server-side
	// search — this filters client-side over whatever's already loaded,
	// same "search what you have in memory" approach the Library page's
	// own search box uses.
	let libraryQuery = $state('');
	const filteredLibrary = $derived.by(() => {
		const needle = libraryQuery.trim().toLowerCase();
		if (!needle) return data.audit ?? [];
		return (data.audit ?? []).filter((a: any) =>
			[a.actor, a.action, a.detail].some((v) => (v ?? '').toLowerCase().includes(needle))
		);
	});

	let adminQuery = $state('');
	const filteredAdminEvents = $derived.by(() => {
		const needle = adminQuery.trim().toLowerCase();
		const events = adminLog?.events ?? [];
		if (!needle) return events;
		return events.filter((a: any) =>
			[a.actor, a.action, a.detail].some((v) => (v ?? '').toLowerCase().includes(needle))
		);
	});

	// A quick visual read on what kind of action a row is — destructive
	// (suspend/reject/delete/remove) reads as a warning, a positive
	// state change (approve/activate/reactivate) reads as confirmation,
	// everything else stays neutral. Pattern-matched against the action
	// string itself since neither backend trail tags a severity.
	function actionTone(action: string): 'danger' | 'ok' | 'neutral' {
		const a = (action ?? '').toLowerCase();
		if (/suspend|reject|delete|remove|revoke/.test(a)) return 'danger';
		if (/approve|activate|reactivate|create/.test(a)) return 'ok';
		return 'neutral';
	}
</script>

<svelte:head><title>Audit history — Admin portal</title></svelte:head>

<!-- Pulled out of "2 · What Functional Health Collab knows" on the Knowledge page, where a
     6-row inline preview crowded a narrow rail panel. Full history (up to
     the 100 most recent events GET /api/audit returns) gets its own screen
     instead. -->
<div class="pane-row"><div class="detail-pane"><div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="history" size={16} /></span><h1>Audit history</h1></div></div>

	<Tabs bind:active tabs={adminLog
		? [{ id: 'library', label: 'Library events' }, { id: 'admin', label: 'Admin actions' }]
		: [{ id: 'library', label: 'Library events' }]} />

	{#if active === 'library'}
		<p class="hint">Library-only events — who changed what in the knowledge base, and when. Each Pro practitioner's own patient-vault activity is separate and isn't shown here.</p>
		<div class="toolbar">
			<div class="search">
				<Icon name="search" size={13} />
				<input type="search" placeholder="Search who, what, or detail…" bind:value={libraryQuery} aria-label="Search library events" />
			</div>
			<span class="hint count">{filteredLibrary.length} of {(data.audit ?? []).length}</span>
		</div>

		<DataTable
			columns={[{ key: 'actor', label: 'Who', sortable: true }, { key: 'action', label: 'Action', sortable: true }, { key: 'detail', label: 'Detail' }, { key: 'ts', label: 'When', sortable: true }]}
			rows={filteredLibrary}
			empty={libraryQuery ? 'Nothing matches that search.' : 'Nothing logged yet.'}
		>
			{#snippet row(a: any)}
				<td>{a.actor}</td>
				<td><Chip tone={actionTone(a.action)}>{a.action}</Chip></td>
				<td>{a.detail ?? ''}</td>
				<td class="when">{(a.ts ?? '').slice(0, 16).replace('T', ' ')}</td>
			{/snippet}
		</DataTable>
	{:else if adminLog}
		<p class="hint">Practitioner approvals/suspensions, plan changes, and admin-account management — a separate Postgres trail from the library events. Superadmin-only.</p>
		<div class="toolbar">
			<div class="search">
				<Icon name="search" size={13} />
				<input type="search" placeholder="Search who, what, or detail…" bind:value={adminQuery} aria-label="Search admin actions" />
			</div>
			<span class="hint count">{filteredAdminEvents.length} of {adminLog.events.length} on this page</span>
		</div>

		<DataTable
			columns={[{ key: 'actor', label: 'Who', sortable: true }, { key: 'action', label: 'Action', sortable: true }, { key: 'detail', label: 'Detail' }, { key: 'ts', label: 'When', sortable: true }]}
			rows={filteredAdminEvents}
			empty={adminQuery ? 'Nothing matches that search.' : 'Nothing logged yet.'}
		>
			{#snippet row(a: any)}
				<td>{a.actor}</td>
				<td><Chip tone={actionTone(a.action)}>{a.action}</Chip></td>
				<td>{a.detail ?? ''}</td>
				<td class="when">{(a.ts ?? '').slice(0, 16).replace('T', ' ')}</td>
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
</div></div>

<style>
	.hint { margin-bottom: var(--space-4); }
	.hint.count { margin-bottom: 0; white-space: nowrap; }
	.toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin: var(--space-4) 0; }
	.search {
		display: flex; align-items: center; gap: .4rem; border: 1px solid var(--line-2); border-radius: 99px;
		background: var(--panel); color: var(--muted); padding: .35rem .8rem; min-width: 16rem; flex: 0 1 24rem;
	}
	.search input { border: none; background: none; font: inherit; font-size: var(--text-sm); color: var(--ink); flex: 1 1 auto; outline: none; }
	.when { color: var(--muted); white-space: nowrap; }
	.pager { display: flex; align-items: center; gap: var(--space-3); margin-top: var(--space-4); }
</style>
