<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { get } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Dialog from '$lib/components/Dialog.svelte';

	let { data } = $props();
	let text = $state('');
	let fileInput = $state<HTMLInputElement>();
	let ingesting = $state(false);

	// Library browser: categories = topics (from /api/coverage, with counts),
	// a kind filter alongside them, and a search box over both. Filtered
	// client-side since the PoC library tops out around a few dozen sources
	// (README "Deliberate PoC limits") and +page.ts already loads up to 200.
	let q = $state('');
	let activeTopic = $state('');
	let activeKind = $state('');

	const filtered = $derived.by(() => {
		const needle = q.trim().toLowerCase();
		return (data.sources ?? []).filter((s: any) => {
			if (activeTopic && !(s.topics ?? []).includes(activeTopic)) return false;
			if (activeKind && s.kind !== activeKind) return false;
			if (!needle) return true;
			return [s.title, s.summary, s.origin, s.author, s.filename]
				.some((v) => (v ?? '').toLowerCase().includes(needle));
		});
	});

	let viewing = $state(false);
	let viewTitle = $state('');
	let viewLoading = $state(false);
	let viewBody = $state<{ body: string; body_reconstructed?: boolean } | null>(null);

	async function viewDoc(s: any) {
		if (s.original_name) {
			window.open(`${PUBLIC_API_BASE}/api/sources/${s.id}/original`, '_blank', 'noopener');
			return;
		}
		viewTitle = s.title;
		viewBody = null;
		viewLoading = true;
		viewing = true;
		try {
			viewBody = await get(fetch, `/sources/${s.id}/text`);
		} catch (err: any) {
			toast(err.message, 'alert');
			viewing = false;
		} finally {
			viewLoading = false;
		}
	}

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
	<input
		class="search"
		type="search"
		placeholder="Search titles, summaries, origins, authors…"
		bind:value={q}
		aria-label="Search the library"
	/>

	<div class="facets">
		<div class="facet-row">
			<span class="facet-label">Category</span>
			<button class="fchip" class:active={!activeTopic} onclick={() => (activeTopic = '')}>
				All <span class="n">{data.sources.length}</span>
			</button>
			{#each data.coverage as c (c.topic)}
				<button class="fchip" class:active={activeTopic === c.topic} onclick={() => (activeTopic = activeTopic === c.topic ? '' : c.topic)}>
					{c.topic} <span class="n">{c.sources}</span>
				</button>
			{/each}
		</div>
		{#if data.kinds.length}
			<div class="facet-row">
				<span class="facet-label">Kind</span>
				<button class="fchip" class:active={!activeKind} onclick={() => (activeKind = '')}>All</button>
				{#each data.kinds as k (k)}
					<button class="fchip" class:active={activeKind === k} onclick={() => (activeKind = activeKind === k ? '' : k)}>{k}</button>
				{/each}
			</div>
		{/if}
	</div>

	<DataTable
		columns={[{ key: 'title', label: 'Title', sortable: true }, { key: 'kind', label: 'Kind' }, { key: 'grade', label: 'Grade', sortable: true }, { key: 'created_at', label: 'Ingested' }, { key: 'view', label: '' }]}
		rows={filtered}
		empty={data.sources.length ? 'Nothing matches those filters.' : 'Nothing ingested yet.'}
	>
		{#snippet row(s: any)}
			<td>
				{s.title}
				{#if s.topics?.length}<div class="topics">{s.topics.join(' · ')}</div>{/if}
			</td>
			<td><Chip tone="neutral">{s.kind}</Chip></td>
			<td>{s.grade}</td>
			<td>{(s.created_at ?? '').slice(0, 10)}</td>
			<td><button class="view" onclick={() => viewDoc(s)}>View</button></td>
		{/snippet}
	</DataTable>
</Spotlight>

<Dialog bind:open={viewing} title={viewTitle}>
	{#if viewLoading}
		<p class="hint">Loading…</p>
	{:else if viewBody}
		{#if viewBody.body_reconstructed}
			<p class="hint">Rebuilt from passages — no original body was stored for this source.</p>
		{/if}
		<div class="doc-body">{viewBody.body}</div>
	{/if}
</Dialog>

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
	.search {
		width: 100%; font-size: var(--text-lg); padding: var(--space-4);
		border: 1px solid var(--line-2); border-radius: var(--r-lg); background: var(--panel);
		color: var(--ink); margin-bottom: var(--space-4);
		transition: border-color .15s var(--ease), box-shadow .15s var(--ease);
	}
	.search:focus {
		outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);
	}
	.facets { display: grid; gap: var(--space-2); margin-bottom: var(--space-4); }
	.facet-row { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; }
	.facet-label {
		font-size: var(--text-xs); font-weight: 650; text-transform: uppercase; letter-spacing: .04em;
		color: var(--muted); margin-right: .3rem;
	}
	.fchip {
		font: inherit; font-size: var(--text-sm); cursor: pointer;
		border: 1px solid var(--line); background: var(--panel-2); color: var(--ink);
		border-radius: 99px; padding: .3rem .7rem; display: inline-flex; align-items: center; gap: .35rem;
		transition: background .15s var(--ease), border-color .15s var(--ease), color .15s var(--ease);
	}
	.fchip:hover { border-color: var(--accent); }
	.fchip.active { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-ink); }
	.fchip .n { color: var(--muted); font-size: var(--text-xs); }
	.fchip.active .n { color: inherit; opacity: .75; }
	.topics { font-size: var(--text-xs); color: var(--muted); margin-top: .15rem; }
	.view {
		font: inherit; font-size: var(--text-sm); font-weight: 650; cursor: pointer;
		border: 1px solid var(--line); background: var(--panel); color: var(--accent-ink);
		border-radius: var(--r); padding: .3rem .7rem;
	}
	.view:hover { border-color: var(--accent); background: var(--accent-soft); }
	.doc-body { white-space: pre-wrap; font-size: var(--text-sm); line-height: 1.6; max-height: 60vh; overflow-y: auto; }
	.field { display: flex; flex-direction: column; gap: .35rem; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .35rem; font-size: var(--text-sm); color: var(--muted); }
</style>
