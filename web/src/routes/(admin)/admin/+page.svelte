<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { get, post, patch, del } from '$lib/api';
	import { chunkedUpload } from '$lib/chunkedUpload';
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
	let staging = $state(false);
	let stageProgress = $state<{ sent: number; total: number } | null>(null);

	// Staged items — uploaded/pasted but not yet promoted into the graph
	// (app/main.py's /api/staged*, specs/v3/18-document-ingest-upgrade.md).
	// "Ingest" below always meant "stage" too until now: every add
	// immediately ran the full Reader/chunk/write pipeline, one at a time,
	// with no way to pile several up first and review before committing.
	let selected = $state<Set<string>>(new Set());
	let promotingId = $state<string | null>(null);
	let promotingBatch = $state(false);

	function toggleSelected(id: string) {
		const next = new Set(selected);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selected = next;
	}

	function stagedFileUrl(item: any) {
		return `${PUBLIC_API_BASE}/api/staged/${item.id}/file`;
	}

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

	// Regrade/delete: PATCH and DELETE /api/sources/{id} always existed on the
	// backend (the pre-rewrite admin page used both, static/app.js) but had no
	// UI in this rewrite — README.md's "a source can be corrected or removed"
	// had no way to do either (specs/v4/04-known-issues.md#h1).
	async function regrade(s: any, grade: number) {
		if (grade === s.grade) return;
		try {
			await patch(fetch, `/sources/${s.id}`, { grade });
			toast(`"${s.title.slice(0, 40)}" set to grade ${grade}.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	let deleting = $state<any>(null);
	let confirmingDelete = $state(false);

	function askDelete(s: any) {
		deleting = s;
		confirmingDelete = true;
	}

	async function confirmDelete() {
		if (!deleting) return;
		const s = deleting;
		confirmingDelete = false;
		try {
			await del(fetch, `/sources/${s.id}`);
			toast('Source removed from the library.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function stageItem(e: Event) {
		e.preventDefault();
		if (!text.trim() && !fileInput?.files?.length) return;
		staging = true;
		stageProgress = null;
		try {
			const file = fileInput?.files?.[0];
			if (file) {
				// Chunked regardless of size: one code path, always shows
				// progress, and never risks a single >200MB-capable request
				// hitting nginx's body-size limit (app/uploads.py, web/src/lib/
				// chunkedUpload.ts). 'stage' instead of 'complete' — lands in
				// the staged list below, not ingested yet.
				await chunkedUpload('/sources', file, {}, (p) => (stageProgress = p), 'stage');
			} else {
				const fd = new FormData();
				fd.set('text', text);
				const res = await fetch(`${PUBLIC_API_BASE}/api/staged`, { method: 'POST', credentials: 'include', body: fd });
				if (!res.ok) {
					const body = await res.json().catch(() => ({}));
					throw new Error(body?.detail?.message || body?.detail || 'Staging failed.');
				}
			}
			toast('Added to the staged list.');
			text = '';
			if (fileInput) fileInput.value = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			staging = false;
			stageProgress = null;
		}
	}

	function clearFiltersAfterIngest() {
		// An active category/kind filter could otherwise hide a source
		// that was just ingested, with nothing telling the admin why it
		// isn't in the list (specs/v4/04-known-issues.md#m16, found in
		// this page's own initial review).
		q = activeTopic = activeKind = '';
	}

	async function ingestOne(id: string) {
		promotingId = id;
		try {
			await post(fetch, `/staged/${id}/ingest`, {});
			toast('Ingested into the library.');
			clearFiltersAfterIngest();
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			promotingId = null;
		}
	}

	async function ingestSelected() {
		if (!selected.size) return;
		promotingBatch = true;
		try {
			const res = await post(fetch, '/staged/ingest', { ids: [...selected] });
			toast(
				res.failed?.length
					? `${res.ingested.length} ingested, ${res.failed.length} failed.`
					: `${res.ingested.length} source(s) ingested.`,
				res.failed?.length ? 'alert' : undefined
			);
			selected = new Set();
			clearFiltersAfterIngest();
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			promotingBatch = false;
		}
	}

	async function discardStaged(id: string) {
		try {
			await del(fetch, `/staged/${id}`);
			toast('Discarded.');
			if (selected.has(id)) {
				const next = new Set(selected);
				next.delete(id);
				selected = next;
			}
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}
</script>

<svelte:head><title>Knowledge — Admin portal</title></svelte:head>

<!-- specs/v4/03: library list stays Tier 1 (the actual work surface); ingest
     and the audit/graph rail demoted to Tier 2 (used far less often) — that's
     visual *weight* (Quiet vs Spotlight), a separate question from spatial
     layout. The spec's own diagnosis of the old static/index.html was three
     panels side by side, not stacked — a narrow side column for the two
     Tier-2 panels alongside the library keeps that spatial shape without
     reverting the weight fix. -->
<div class="layout">
<div class="side">
<Quiet title="1 · Teach Clinic">
	<form onsubmit={stageItem} class="ingest">
		<TextField label="Paste text" type="textarea" bind:value={text} placeholder="Paste an article, note, or transcript…" />
		<div class="field">
			<label for="file">Or upload a file</label>
			<input id="file" type="file" bind:this={fileInput} />
			<p class="hint">Up to 200 MB — sent in pieces, so a large PDF doesn't need one giant request.</p>
		</div>
		{#if stageProgress}
			<div class="upload-progress">
				<div class="bar" style="width: {Math.round((stageProgress.sent / stageProgress.total) * 100)}%"></div>
				<span class="hint">{Math.round(stageProgress.sent / 1024 / 1024)} / {Math.round(stageProgress.total / 1024 / 1024)} MB</span>
			</div>
		{/if}
		<Button type="submit" loading={staging}>Add to staged list</Button>
	</form>

	{#if data.staged?.length}
		<div class="staged">
			<div class="staged-head">
				<strong>Staged — not yet in the library ({data.staged.length})</strong>
				<Button variant="outlined" onclick={ingestSelected} loading={promotingBatch} disabled={!selected.size}>
					Ingest selected ({selected.size})
				</Button>
			</div>
			<ul class="staged-list">
				{#each data.staged as item (item.id)}
					<li class="staged-item">
						<input
							type="checkbox"
							checked={selected.has(item.id)}
							onchange={() => toggleSelected(item.id)}
							aria-label="Select {item.filename ?? 'pasted text'}"
						/>
						<div class="staged-body">
							<div class="staged-title">
								{item.filename ?? 'Pasted text'}
								<Chip tone="neutral">{item.kind}</Chip>
								{#if item.page_count}<span class="hint">{item.page_count} page(s)</span>{/if}
							</div>
							<p class="staged-preview">{item.preview}{item.preview?.length >= 280 ? '…' : ''}</p>
						</div>
						<div class="staged-actions">
							{#if item.kind === 'file'}
								<a class="view" href={stagedFileUrl(item)} target="_blank" rel="noopener">View</a>
							{/if}
							<button class="view" onclick={() => ingestOne(item.id)} disabled={promotingId === item.id}>
								{promotingId === item.id ? 'Ingesting…' : 'Ingest'}
							</button>
							<button class="view danger" onclick={() => discardStaged(item.id)}>Discard</button>
						</div>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
</Quiet>

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
</div>

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
		columns={[{ key: 'title', label: 'Title', sortable: true }, { key: 'kind', label: 'Kind' }, { key: 'grade', label: 'Grade', sortable: true }, { key: 'created_at', label: 'Ingested' }, { key: 'actions', label: '' }]}
		rows={filtered}
		empty={data.sources.length ? 'Nothing matches those filters.' : 'Nothing ingested yet.'}
	>
		{#snippet row(s: any)}
			<td>
				{s.title}
				{#if s.reader_truncated}<Chip tone="warn">graded from a partial read</Chip>{/if}
				{#if s.topics?.length}<div class="topics">{s.topics.join(' · ')}</div>{/if}
			</td>
			<td><Chip tone="neutral">{s.kind}</Chip></td>
			<td>
				<input
					class="grade"
					type="number" min="1" max="10" value={s.grade}
					onchange={(e) => regrade(s, Number((e.target as HTMLInputElement).value))}
				/>
			</td>
			<td>{(s.created_at ?? '').slice(0, 10)}</td>
			<td class="actions">
				<button class="view" onclick={() => viewDoc(s)}>View</button>
				<button class="view danger" onclick={() => askDelete(s)}>Remove</button>
			</td>
		{/snippet}
	</DataTable>
</Spotlight>
</div>

<Dialog bind:open={confirmingDelete} title="Remove source">
	{#if deleting}
		<p>Remove "{deleting.title}" and its {deleting.chunks ?? 0} passage(s)? Answers will stop citing it.</p>
	{/if}
	{#snippet footer()}
		<button class="view" onclick={() => (confirmingDelete = false)}>Keep</button>
		<button class="view danger" onclick={confirmDelete}>Remove</button>
	{/snippet}
</Dialog>

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

<style>
	.layout { display: grid; grid-template-columns: 22rem 1fr; gap: var(--space-5); align-items: start; }
	.side { display: grid; gap: var(--space-5); }
	@media (max-width: 960px) { .layout { grid-template-columns: 1fr; } }
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
	.view.danger { color: var(--danger); }
	.view.danger:hover { border-color: var(--danger); background: var(--danger-soft); }
	td.actions { display: flex; gap: .4rem; }
	input.grade {
		width: 3.5rem; border: 1px solid var(--line-2); border-radius: var(--r);
		padding: .3rem .4rem; font: inherit; color: var(--ink); background: var(--panel);
	}
	.doc-body { white-space: pre-wrap; font-size: var(--text-sm); line-height: 1.6; max-height: 60vh; overflow-y: auto; }
	.field { display: flex; flex-direction: column; gap: .35rem; }
	.staged { margin-top: var(--space-5); padding-top: var(--space-4); border-top: 1px solid var(--glass-line); display: grid; gap: var(--space-3); }
	.staged-head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; }
	.staged-list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
	.staged-item { display: flex; gap: var(--space-3); align-items: flex-start; padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--r); }
	.staged-item input[type='checkbox'] { margin-top: .3rem; }
	.staged-body { flex: 1 1 auto; min-width: 0; }
	.staged-title { display: flex; align-items: center; gap: .4rem; font-weight: 650; flex-wrap: wrap; }
	.staged-preview { margin: .3rem 0 0; font-size: var(--text-sm); color: var(--muted); overflow-wrap: anywhere; }
	.staged-actions { display: flex; gap: .35rem; flex: 0 0 auto; flex-wrap: wrap; }
	.view:disabled { opacity: .5; cursor: not-allowed; }
	.upload-progress {
		display: flex; align-items: center; gap: var(--space-3);
		background: var(--panel-2); border-radius: 99px; padding: .35rem .35rem .35rem .1rem;
	}
	.upload-progress .bar { flex: 1 1 auto; height: 6px; border-radius: 99px; background: var(--accent); transition: width .2s var(--ease); margin-left: .25rem; }
	.upload-progress .hint { flex: 0 0 auto; padding-right: .5rem; white-space: nowrap; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .35rem; font-size: var(--text-sm); color: var(--muted); }
</style>
