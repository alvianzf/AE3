<script lang="ts">
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();
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
</Spotlight>

<style>
	.hint { margin-bottom: var(--space-4); }
</style>
