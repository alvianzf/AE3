<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Column { key: string; label: string; sortable?: boolean }

	let {
		columns,
		rows,
		row,
		empty = 'Nothing here yet.'
	}: {
		columns: Column[];
		rows: Record<string, unknown>[];
		row: Snippet<[Record<string, unknown>]>;
		empty?: string;
	} = $props();

	let sortKey = $state('');
	let sortDir = $state(1);

	const sorted = $derived.by(() => {
		if (!sortKey) return rows;
		const copy = [...rows];
		copy.sort((a, b) => {
			const av = a[sortKey], bv = b[sortKey];
			if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sortDir;
			return String(av ?? '').localeCompare(String(bv ?? '')) * sortDir;
		});
		return copy;
	});

	function sortBy(key: string) {
		if (sortKey === key) sortDir *= -1;
		else { sortKey = key; sortDir = 1; }
	}
</script>

<div class="scroll-x">
	<table class="data-table">
		<thead>
			<tr>
				{#each columns as col (col.key)}
					<th>
						{#if col.sortable}
							<button class="sort" onclick={() => sortBy(col.key)}>
								{col.label}
								{#if sortKey === col.key}<span>{sortDir === 1 ? '▲' : '▼'}</span>{/if}
							</button>
						{:else}
							{col.label}
						{/if}
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each sorted as r (r.id ?? JSON.stringify(r))}
				<tr>{@render row(r)}</tr>
			{:else}
				<tr><td colspan={columns.length} class="empty">{empty}</td></tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.data-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
	.data-table th {
		text-align: left; padding: var(--space-3); border-bottom: 1px solid var(--line);
		color: var(--muted); font-weight: 650; font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .04em;
	}
	.data-table :global(td) { padding: var(--space-3); border-bottom: 1px solid var(--line); vertical-align: middle; }
	.data-table tbody tr:hover { background: var(--panel-2); }
	.sort { border: none; background: none; font: inherit; color: inherit; font-weight: 650; text-transform: uppercase; letter-spacing: .04em; font-size: var(--text-xs); cursor: pointer; display: inline-flex; gap: .3rem; }
	.empty { text-align: center; color: var(--muted); padding: var(--space-6); }
</style>
