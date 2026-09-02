<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	let text = $state('');
	let fileInput = $state<HTMLInputElement>();
	let ingesting = $state(false);

	async function ingest(e: Event) {
		e.preventDefault();
		if (!text.trim() && !fileInput?.files?.length) return;
		ingesting = true;
		const fd = new FormData();
		if (fileInput?.files?.[0]) fd.set('file', fileInput.files[0]);
		else fd.set('text', text);
		try {
			const res = await fetch(`${PUBLIC_API_BASE}/api/sources`, { method: 'POST', credentials: 'include', body: fd });
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				throw new Error(body?.detail?.message || body?.detail || 'Ingest failed.');
			}
			toast('Source ingested.');
			text = '';
			if (fileInput) fileInput.value = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			ingesting = false;
		}
	}
</script>

<svelte:head><title>Knowledge — Admin portal</title></svelte:head>

<!-- specs/v4/03: library list stays Tier 1 (the actual work surface); ingest
     and the audit/graph rail demoted to Tier 2 (used far less often). -->
<Quiet title="1 · Teach Clinic">
	<form onsubmit={ingest} class="ingest">
		<TextField label="Paste text" type="textarea" bind:value={text} placeholder="Paste an article, note, or transcript…" />
		<div class="field">
			<label for="file">Or upload a file</label>
			<input id="file" type="file" bind:this={fileInput} />
		</div>
		<Button type="submit" loading={ingesting}>Ingest</Button>
	</form>
</Quiet>

<Spotlight title="2 · The library">
	<DataTable
		columns={[{ key: 'title', label: 'Title', sortable: true }, { key: 'kind', label: 'Kind' }, { key: 'grade', label: 'Grade', sortable: true }, { key: 'created_at', label: 'Ingested' }]}
		rows={data.sources}
		empty="Nothing ingested yet."
	>
		{#snippet row(s)}
			<td>{s.title}</td>
			<td><Chip tone="neutral">{s.kind}</Chip></td>
			<td>{s.grade}</td>
			<td>{(s.created_at ?? '').slice(0, 10)}</td>
		{/snippet}
	</DataTable>
</Spotlight>

<Quiet title="3 · What Clinic knows">
	{#if data.graph}
		<p class="hint">{data.graph.node_count ?? 0} concepts · {data.graph.edge_count ?? 0} links · {(data.graph.unlinked ?? []).length} unlinked sources</p>
	{/if}
	{#if data.audit?.length}
		<ul class="list">
			{#each data.audit.slice(0, 6) as a (a.id ?? a.created_at)}
				<li>{a.action ?? a.event} — {(a.created_at ?? '').slice(0, 16).replace('T', ' ')}</li>
			{/each}
		</ul>
	{/if}
</Quiet>

<style>
	.ingest { display: grid; gap: var(--space-3); }
	.field { display: flex; flex-direction: column; gap: .35rem; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .35rem; font-size: var(--text-sm); color: var(--muted); }
</style>
