<script lang="ts">
	let { data } = $props();
	const isPro = $derived(data.profile?.plan === 'pro');

	const steps = $derived([
		{ label: 'Add your first client', done: (data.clients?.length ?? 0) > 0, href: '/practitioner/clients' },
		{ label: 'Ask your first question in Consult', done: (data.recentSessions?.length ?? 0) > 0, href: '/practitioner/consult' }
	]);
	const showChecklist = $derived(isPro && !steps.every((s) => s.done));

	const rows = $derived.by(() => {
		const intake = data.notifications?.unviewed_intake ?? 0;
		const newContacts = data.notifications?.new_contacts ?? 0;
		return [
			{ label: 'Consults logged', value: data.recentSessions?.length ?? 0, href: '/practitioner/consult' },
			{ label: 'Clients', value: data.clients?.length ?? 0, href: '/practitioner/clients' },
			{ label: 'Unviewed intake', value: intake, href: '/practitioner/clients', warn: intake > 0 },
			{ label: 'New contact submissions', value: newContacts, href: '/practitioner/contacts', warn: newContacts > 0 }
		];
	});
</script>

<svelte:head><title>Overview — Practitioner portal</title></svelte:head>

<div class="pane-row">
	<div class="detail-pane">
		<div class="detail-head"><div><h1>Overview</h1><p>Welcome back.</p></div></div>

		{#if showChecklist}
			<div class="checklist">
				<span class="checklist-label">Getting started</span>
				{#each steps as s (s.label)}
					<a class="checklist-item" class:done={s.done} href={s.href}>
						<span class="mark" aria-hidden="true">{s.done ? '✓' : '○'}</span>{s.label}
					</a>
				{/each}
			</div>
		{/if}

		<div class="stat-list">
			{#each rows as r (r.label)}
				<a class="stat-row" class:warn={r.warn} href={r.href}>
					<span>{r.label}</span><strong>{r.value}</strong>
				</a>
			{/each}
		</div>
	</div>
</div>

<style>
	.checklist {
		display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap;
		border: 1px solid var(--line); background: var(--panel-2);
		padding: var(--space-3) var(--space-4); margin-bottom: var(--space-5); font-size: var(--text-sm);
	}
	.checklist-label { font-weight: 650; color: var(--ink-2); }
	.checklist-item { display: flex; align-items: center; gap: .4rem; text-decoration: none; color: var(--ink); }
	.checklist-item.done { color: var(--muted); text-decoration: line-through; }
	.mark { font-weight: 700; }
	.stat-list { border-top: 1px solid var(--line); max-width: 28rem; }
	.stat-row {
		display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) 0;
		border-bottom: 1px solid var(--line); color: var(--ink); text-decoration: none;
	}
	.stat-row.warn strong { color: var(--warn); }
	a.stat-row:hover { color: var(--accent-ink); }
</style>
