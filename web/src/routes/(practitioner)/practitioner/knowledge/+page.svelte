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
</script>

<svelte:head><title>Knowledge — Practitioner portal</title></svelte:head>

<Spotlight title="Your knowledge weighting">
	<p class="hint">Boost or dampen how much each shared library source counts when your consults run.</p>
	<DataTable
		columns={[{ key: 'title', label: 'Source', sortable: true }, { key: 'grade', label: 'Grade' }, { key: 'weight', label: 'Your weight' }]}
		rows={data.sources}
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
</Spotlight>

<style>
	input[type='number'] { width: 4rem; border: 1px solid var(--line-2); border-radius: var(--r); padding: .3rem .5rem; }
</style>
