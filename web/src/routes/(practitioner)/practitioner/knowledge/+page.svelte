<script lang="ts">
	import { put } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();

	async function setWeight(id: string, weight: number) {
		try {
			await put(fetch, `/me/knowledge/${id}/weight`, { weight });
			toast('Weight updated.');
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	// specs/v4.1/03 H4 — this screen mirrored the admin Library's unbounded
	// list before that page got search + pagination; bring the same two
	// mechanisms here so it doesn't degrade faster as the library grows.
	let q = $state('');
	const filtered = $derived.by(() => {
		const needle = q.trim().toLowerCase();
		if (!needle) return data.sources;
		return data.sources.filter((s: any) => (s.title ?? '').toLowerCase().includes(needle));
	});

	const PER_PAGE = 12;
	let page = $state(1);
	const totalPages = $derived(Math.max(1, Math.ceil(filtered.length / PER_PAGE)));
	const shownPage = $derived(Math.min(page, totalPages));
	const pageItems = $derived.by(() => {
		const start = (shownPage - 1) * PER_PAGE;
		return filtered.slice(start, start + PER_PAGE);
	});
</script>

<svelte:head><title>Library weights — Practitioner portal</title></svelte:head>

<Spotlight title="Your knowledge weighting">
	<p class="hint">Boost or dampen how much each shared library source counts when your consults run.</p>
	<input class="search" type="search" placeholder="Search by title…" bind:value={q} aria-label="Search library sources" />
	<DataTable
		columns={[{ key: 'title', label: 'Source', sortable: true }, { key: 'grade', label: 'Grade' }, { key: 'weight', label: 'Your weight' }]}
		rows={pageItems}
		empty="Nothing in the library yet."
	>
		{#snippet row(s)}
			<td>{s.title}</td>
			<td><Chip tone="neutral">grade {s.grade}</Chip></td>
			<td>
				<input type="number" min="0" max="5" value={s.weight} onchange={(e) => setWeight(s.id as string, Number((e.target as HTMLInputElement).value))} />
			</td>
		{/snippet}
	</DataTable>
	{#if totalPages > 1}
		<div class="pager">
			<button type="button" disabled={shownPage <= 1} onclick={() => (page = shownPage - 1)}>Previous</button>
			<span class="hint">Page {shownPage} of {totalPages}</span>
			<button type="button" disabled={shownPage >= totalPages} onclick={() => (page = shownPage + 1)}>Next</button>
		</div>
	{/if}
</Spotlight>

<style>
	input[type='number'] { width: 4rem; border: 1px solid var(--line-2); border-radius: var(--r); padding: .3rem .5rem; }
	.search {
		border: 1px solid var(--line-2); border-radius: 99px; padding: .5rem 1rem; margin-bottom: var(--space-3);
		background: var(--panel); font-size: var(--text-sm); min-height: var(--tap-min); width: 100%; max-width: 20rem;
	}
	.pager { display: flex; align-items: center; gap: var(--space-3); margin-top: var(--space-3); }
	.pager button {
		border: 1px solid var(--line-2); border-radius: var(--r); padding: .4rem .8rem; background: var(--panel);
		font: inherit; cursor: pointer;
	}
	.pager button:disabled { opacity: .5; cursor: default; }
</style>
