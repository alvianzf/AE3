<script lang="ts">
	let { data } = $props();
	const s = $derived(data.stats ?? {});

	// Rail navigation reaches every section directly now — this page is
	// just a quick read on the platform, not a launcher. A flat list of
	// facts, not stat tiles in boxes.
	const rows = $derived([
		{ label: 'Pending applications', value: s.pending_practitioners ?? 0, href: '/admin/users', warn: (s.pending_practitioners ?? 0) > 0 },
		{ label: 'Approved practitioners', value: s.approved_practitioners ?? 0, href: '/admin/users' },
		{ label: 'New contact submissions', value: s.new_contacts ?? 0, href: '/admin/users', warn: (s.new_contacts ?? 0) > 0 },
		{ label: 'Total profile views', value: s.total_views ?? 0 }
	]);
</script>

<svelte:head><title>Overview — Admin portal</title></svelte:head>

<div class="pane-row">
	<div class="detail-pane">
		<div class="detail-head"><div><h1>Overview</h1><p>A quick read on the whole platform.</p></div></div>
		<div class="stat-list">
			{#each rows as r (r.label)}
				{#if r.href}
					<a class="stat-row" class:warn={r.warn} href={r.href}>
						<span>{r.label}</span><strong>{r.value}</strong>
					</a>
				{:else}
					<div class="stat-row"><span>{r.label}</span><strong>{r.value}</strong></div>
				{/if}
			{/each}
		</div>
	</div>
</div>

<style>
	.stat-list { border-top: 1px solid var(--line); max-width: 28rem; }
	.stat-row {
		display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) 0;
		border-bottom: 1px solid var(--line); color: var(--ink); text-decoration: none;
	}
	.stat-row.warn strong { color: var(--warn); }
	a.stat-row:hover { color: var(--accent-ink); }
</style>
