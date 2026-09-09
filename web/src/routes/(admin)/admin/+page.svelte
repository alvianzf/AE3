<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { get, post, patch, del } from '$lib/api';
	import { chunkedUpload } from '$lib/chunkedUpload';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import Tabs from '$lib/components/Tabs.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Dialog from '$lib/components/Dialog.svelte';

	let { data } = $props();
	let ingestOpen = $state(false);
	let ingestTab = $state('upload');
	let mainTab = $state('library');
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

	// --- Upload tab: drag-and-drop with a preview (native <embed> for a
	// PDF — same "browsers already render this, no PDF.js dependency
	// needed" approach specs/v3/18 used for the pre-rewrite dropzone) ---
	let dragOver = $state(false);
	let selectedFile = $state<File | null>(null);
	let previewUrl = $state<string | null>(null);

	function pickFile(file: File | null) {
		if (previewUrl) URL.revokeObjectURL(previewUrl);
		selectedFile = file;
		previewUrl = file ? URL.createObjectURL(file) : null;
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		pickFile(e.dataTransfer?.files?.[0] ?? null);
	}

	function onFileInputChange(e: Event) {
		pickFile((e.target as HTMLInputElement).files?.[0] ?? null);
	}

	async function stageFile() {
		if (!selectedFile) return;
		staging = true;
		stageProgress = null;
		try {
			// Chunked regardless of size: one code path, always shows
			// progress, and never risks a single >200MB-capable request
			// hitting nginx's body-size limit (app/uploads.py, web/src/lib/
			// chunkedUpload.ts). 'stage' instead of 'complete' — lands in
			// the staged list below, not ingested yet.
			await chunkedUpload('/sources', selectedFile, {}, (p) => (stageProgress = p), 'stage');
			toast('Added to the staged list.');
			pickFile(null);
			if (fileInput) fileInput.value = '';
			ingestOpen = false;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			staging = false;
			stageProgress = null;
		}
	}

	// --- Paste-text tab ---
	async function stageText(e: Event) {
		e.preventDefault();
		if (!text.trim()) return;
		staging = true;
		try {
			const fd = new FormData();
			fd.set('text', text);
			const res = await fetch(`${PUBLIC_API_BASE}/api/staged`, { method: 'POST', credentials: 'include', body: fd });
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				throw new Error(body?.detail?.message || body?.detail || 'Staging failed.');
			}
			toast('Added to the staged list.');
			text = '';
			ingestOpen = false;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			staging = false;
		}
	}

	// --- Enter-URL tab: fetch, strip, extract via Haiku (app/scraper.py +
	// llm.extract_article()) — content only, no chrome, never summarized ---
	let url = $state('');
	let scraping = $state(false);

	async function scrapeUrl(e: Event) {
		e.preventDefault();
		if (!url.trim()) return;
		scraping = true;
		try {
			await post(fetch, '/scrape', { url: url.trim() });
			toast('Scraped and added to the staged list.');
			url = '';
			ingestOpen = false;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			scraping = false;
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

<!-- specs/v4/03: library list stays Tier 1 (the actual work surface); the
     staged-review queue and the audit/graph rail demoted to Tier 2 (used far
     less often) — that's visual *weight* (Quiet vs Spotlight), a separate
     question from spatial layout. Teaching Clinic (upload/paste/scrape) is
     now an on-demand modal reached via the library's "+ Add resources"
     action rather than a permanent rail panel — it's a write action, not
     something to browse, and pulling it out of the rail leaves one clear
     list there ("staged for review") instead of the upload form and the
     review queue competing for the same space (source of the "what are
     these two lists" confusion this page kept getting reported for). -->
<div class="rail-layout">
<div class="rail">
<Quiet title="2 · What Clinic knows">
	{#if data.graph}
		<p class="hint">{data.graph.concepts ?? 0} concepts · {data.graph.mentions ?? 0} links · {(data.graph.unlinked ?? []).length} unlinked sources</p>
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

<Spotlight title="1 · Knowledge library" actions={libraryActions}>
	<Tabs
		bind:active={mainTab}
		tabs={[
			{ id: 'library', label: 'Library' },
			{ id: 'staged', label: data.staged?.length ? `Staged for review (${data.staged.length})` : 'Staged for review' }
		]}
	/>

	<div class="tab-panel">
	{#if mainTab === 'library'}
		<div class="search-bar">
			<input
				class="search"
				type="search"
				placeholder="Search titles, summaries, origins, authors…"
				bind:value={q}
				aria-label="Search the library"
			/>
			{#if q}
				<button class="search-clear" onclick={() => (q = '')} aria-label="Clear search">&times;</button>
			{/if}
		</div>

		{#if !q && !activeTopic}
			<!-- DMOZ-style directory front page: categories only, no document
			     list yet — https://dmoz-odp.com/ shows the same shape. Topic is
			     the only hierarchy the graph actually has (Neo4j has no
			     subcategory nodes), so "subcategory" below is Kind, a facet
			     applied once a category is opened rather than a second real
			     tier — an honest read of a flat data model, not a fake nesting. -->
			<div class="directory-grid">
				{#each data.coverage as c (c.topic)}
					<button class="dir-tile" onclick={() => (activeTopic = c.topic)}>
						<span class="dir-name">{c.topic}</span>
						<span class="dir-count">{c.sources} document{c.sources === 1 ? '' : 's'}</span>
					</button>
				{/each}
			</div>
			{#if !data.coverage.length}
				<p class="hint">Nothing ingested yet — use "+ Add resources" to start teaching Clinic.</p>
			{/if}
		{:else}
			<div class="breadcrumb">
				<button class="crumb" onclick={() => { activeTopic = ''; activeKind = ''; }}>All categories</button>
				{#if activeTopic}<span class="sep">›</span><span class="crumb current">{activeTopic}</span>{/if}
				{#if q}<span class="sep">›</span><span class="crumb current">Search: "{q}"</span>{/if}
			</div>

			{#if data.kinds.length}
				<div class="facets">
					<div class="facet-row">
						<span class="facet-label">Kind</span>
						<button class="fchip" class:active={!activeKind} onclick={() => (activeKind = '')}>All</button>
						{#each data.kinds as k (k)}
							<button class="fchip" class:active={activeKind === k} onclick={() => (activeKind = activeKind === k ? '' : k)}>{k}</button>
						{/each}
					</div>
				</div>
			{/if}

			<DataTable
				columns={[{ key: 'title', label: 'Title', sortable: true }, { key: 'kind', label: 'Kind' }, { key: 'grade', label: 'Grade', sortable: true }, { key: 'created_at', label: 'Ingested' }, { key: 'actions', label: '' }]}
				rows={filtered}
				empty={data.sources.length ? 'Nothing matches those filters.' : 'Nothing ingested yet.'}
			>
				{#snippet row(s: any)}
					<td>
						{s.title}
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
		{/if}
	{:else}
		{#if data.staged?.length}
			<div class="staged">
				<div class="staged-head">
					<strong>{data.staged.length} not yet in the library</strong>
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
									{item.filename ?? item.source_url ?? 'Pasted text'}
									<Chip tone="neutral">{item.kind === 'scraped_url' ? 'scraped' : item.kind}</Chip>
									{#if item.page_count}<span class="hint">{item.page_count} page(s)</span>{/if}
								</div>
								<p class="staged-preview">{item.preview}{item.preview?.length >= 280 ? '…' : ''}</p>
							</div>
							<div class="staged-actions">
								{#if item.kind === 'file'}
									<a class="view" href={stagedFileUrl(item)} target="_blank" rel="noopener">View</a>
								{:else if item.kind === 'scraped_url'}
									<a class="view" href={item.source_url} target="_blank" rel="noopener">Source</a>
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
		{:else}
			<p class="hint">Nothing staged. Use "+ Add resources" above to upload a document, paste text, or scrape a URL — it lands here for review before it's ingested.</p>
		{/if}
	{/if}
	</div>
</Spotlight>
</div>

{#snippet libraryActions()}
	<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>
{/snippet}

<Dialog bind:open={ingestOpen} title="Add resources" wide>
	<Tabs bind:active={ingestTab} tabs={[{ id: 'upload', label: 'Upload a document' }, { id: 'text', label: 'Paste text' }, { id: 'url', label: 'Enter URL' }]} />

	<div class="ingest-panel">
		{#if ingestTab === 'upload'}
			<input id="file" type="file" bind:this={fileInput} onchange={onFileInputChange} hidden />
			<div
				class="dropzone"
				class:dragover={dragOver}
				class:has-file={!!selectedFile}
				role="button"
				tabindex="0"
				ondragover={(e) => { e.preventDefault(); dragOver = true; }}
				ondragleave={() => (dragOver = false)}
				ondrop={onDrop}
				onclick={() => fileInput?.click()}
				onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput?.click(); } }}
			>
				{#if !selectedFile}
					<p class="dz-title">Drag a file here, or click to browse</p>
					<p class="hint">Up to 200 MB.</p>
				{:else if previewUrl && selectedFile.type === 'application/pdf'}
					<embed src={previewUrl} type="application/pdf" class="pdf-preview" aria-label="{selectedFile.name} preview" />
					<p class="dz-filename">{selectedFile.name}</p>
				{:else}
					<p class="dz-title">{selectedFile.name}</p>
					<p class="hint">{Math.round(selectedFile.size / 1024)} KB</p>
				{/if}
			</div>
			{#if stageProgress}
				<div class="upload-progress">
					<div class="bar" style="width: {Math.round((stageProgress.sent / stageProgress.total) * 100)}%"></div>
					<span class="hint">{Math.round(stageProgress.sent / 1024 / 1024)} / {Math.round(stageProgress.total / 1024 / 1024)} MB</span>
				</div>
			{/if}
			<div class="dz-actions">
				{#if selectedFile}<Button variant="ghost" onclick={() => pickFile(null)}>Clear</Button>{/if}
				<Button onclick={stageFile} loading={staging} disabled={!selectedFile}>Add to staged list</Button>
			</div>
		{:else if ingestTab === 'text'}
			<form onsubmit={stageText} class="ingest">
				<TextField label="Paste text" type="textarea" bind:value={text} placeholder="Paste an article, note, or transcript…" />
				<Button type="submit" loading={staging}>Add to staged list</Button>
			</form>
		{:else if ingestTab === 'url'}
			<form onsubmit={scrapeUrl} class="ingest">
				<TextField label="Page URL" bind:value={url} placeholder="https://…" required />
				<p class="hint">Fetches the page and extracts its content only — no navigation, headers, footers, or ads — via a bounded AI pass. Nothing is summarized or rephrased.</p>
				{#if scraping}
					<div class="scrape-progress" aria-hidden="true"><div class="bar"></div></div>
					<p class="hint">Fetching and extracting…</p>
				{/if}
				<Button type="submit" loading={scraping}>Scrape and add to staged list</Button>
			</form>
		{/if}
	</div>
</Dialog>

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
	.ingest { display: grid; gap: var(--space-3); }
	.ingest-panel { margin-top: var(--space-4); display: grid; gap: var(--space-3); }
	.tab-panel { margin-top: var(--space-4); }
	.dropzone {
		display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .3rem;
		min-height: 8rem; padding: var(--space-4); text-align: center; cursor: pointer;
		border: 2px dashed var(--line-2); border-radius: var(--r-lg); background: var(--panel-2);
		transition: border-color .15s var(--ease), background .15s var(--ease);
	}
	.dropzone:hover, .dropzone:focus-visible { border-color: var(--accent); outline: none; }
	.dropzone.dragover { border-color: var(--accent); background: var(--accent-soft); }
	.dropzone.has-file { cursor: default; padding: var(--space-3); }
	.dz-title { font-weight: 650; }
	.dz-filename { font-weight: 650; font-size: var(--text-sm); margin-top: .3rem; }
	.dz-actions { display: flex; justify-content: flex-end; gap: var(--space-2); }
	.pdf-preview { width: 100%; height: 20rem; border: none; border-radius: var(--r); }
	.scrape-progress { height: 4px; border-radius: 99px; background: var(--panel-2); overflow: hidden; }
	.scrape-progress .bar {
		height: 100%; width: 40%; background: var(--accent); border-radius: 99px;
		animation: scrape-indeterminate 1.2s ease-in-out infinite;
	}
	@keyframes scrape-indeterminate {
		0% { transform: translateX(-120%); }
		100% { transform: translateX(280%); }
	}
	@media (prefers-reduced-motion: reduce) {
		.scrape-progress .bar { animation: none; width: 100%; }
	}
	.search-bar { position: relative; margin-bottom: var(--space-4); }
	.search {
		width: 100%; font-size: var(--text-lg); padding: var(--space-4) var(--space-5) var(--space-4) var(--space-4);
		border: 1px solid var(--line-2); border-radius: var(--r-lg); background: var(--panel);
		color: var(--ink);
		transition: border-color .15s var(--ease), box-shadow .15s var(--ease);
	}
	.search:focus {
		outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);
	}
	.search-clear {
		position: absolute; right: var(--space-3); top: 50%; transform: translateY(-50%);
		border: none; background: none; cursor: pointer; font-size: 1.3rem; line-height: 1;
		color: var(--muted); padding: .2rem .4rem;
	}
	.search-clear:hover { color: var(--ink); }
	.directory-grid {
		display: grid; grid-template-columns: repeat(auto-fill, minmax(11rem, 1fr)); gap: var(--space-3);
	}
	.dir-tile {
		display: flex; flex-direction: column; gap: .3rem; text-align: left; cursor: pointer;
		font: inherit; border: 1px solid var(--line); background: var(--panel-2); color: var(--ink);
		border-radius: var(--r-lg); padding: var(--space-4);
		transition: border-color .15s var(--ease), background .15s var(--ease), transform .15s var(--ease);
	}
	.dir-tile:hover { border-color: var(--accent); background: var(--accent-soft); transform: translateY(-1px); }
	.dir-name { font-weight: 650; }
	.dir-count { font-size: var(--text-sm); color: var(--muted); }
	.breadcrumb { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; margin-bottom: var(--space-3); font-size: var(--text-sm); }
	.crumb {
		font: inherit; cursor: pointer; border: none; background: none; padding: 0;
		color: var(--accent-ink); text-decoration: underline; text-underline-offset: .15em;
	}
	.crumb.current { color: var(--muted); text-decoration: none; cursor: default; font-weight: 650; }
	.breadcrumb .sep { color: var(--muted); }
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
	.staged { display: grid; gap: var(--space-3); }
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
