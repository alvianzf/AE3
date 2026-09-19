<script lang="ts">
	import { onDestroy } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { get, put, post, del, ApiError } from '$lib/api';
	import { chunkedUpload } from '$lib/chunkedUpload';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import Tabs from '$lib/components/Tabs.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();

	// --- Upload — only reachable at all when data.canUploadLibrary is true
	// (backend: app/auth.py's require_admin_or_upload_permitted_practitioner);
	// this is a deliberate duplicate of the admin Library page's own
	// upload/staged-list UI (file + paste-text only, not scrape-URL) rather
	// than a shared component — the first practitioner-facing copy of it. ---
	let ingestOpen = $state(false);
	let ingestTab = $state('upload');
	let text = $state('');
	let fileInput = $state<HTMLInputElement>();
	let staging = $state(false);
	let stageProgress = $state<{ sent: number; total: number } | null>(null);
	let dragOver = $state(false);
	let selectedFile = $state<File | null>(null);
	let previewUrl = $state<string | null>(null);
	let promotingId = $state<string | null>(null);

	// Ingestion jobs: same backgrounded-promotion scheme as the admin
	// Library page (web/src/routes/(admin)/admin/+page.svelte) — promoting a
	// staged item returns a job id immediately (app/main.py's POST
	// /api/staged/{id}/ingest) instead of the finished document, polled
	// here by staged_id, and resumed on load from GET
	// /api/ingestion-jobs/active (+page.ts) so progress survives a reload.
	let jobsByStagedId = $state<Record<string, any>>({});
	const pollTimers: Record<string, ReturnType<typeof setInterval>> = {};

	function jobLabel(job: any): string {
		if (job.status === 'error') return `Failed: ${job.error_message ?? 'unknown error'}`;
		switch (job.step) {
			case 'queued': return 'Queued…';
			case 'reading': return 'Reading document…';
			case 'chunking': return 'Splitting into passages…';
			case 'embedding': return 'Embedding chunks…';
			case 'extracting_graph': return `Extracting knowledge graph (${job.step_detail ?? '…'})…`;
			case 'writing': return 'Writing to library…';
			default: return 'Ingesting…';
		}
	}

	const JOB_STEPS = ['queued', 'reading', 'chunking', 'embedding', 'extracting_graph', 'writing', 'done'];

	function jobProgressPercent(job: any): number {
		const idx = Math.max(0, JOB_STEPS.indexOf(job.step));
		const stepSpan = 1 / (JOB_STEPS.length - 1);
		let within = 0;
		if (job.step === 'extracting_graph' && job.step_detail) {
			const m = /^(\d+) of (\d+)/.exec(job.step_detail);
			if (m) within = Number(m[1]) / Math.max(1, Number(m[2]));
		}
		return Math.min(100, Math.round((idx * stepSpan + within * stepSpan) * 100));
	}

	function watchJob(stagedId: string, jobId: string) {
		if (pollTimers[stagedId]) clearInterval(pollTimers[stagedId]);
		// Set synchronously, before the first poll's network round-trip
		// resolves — same reasoning as the admin Library page's watchJob:
		// without this, ingestOne's `finally` clears promotingId right
		// after calling watchJob, leaving a window where the Ingest button
		// is neither disabled nor labeled "Ingesting…" even though a job is
		// already running server-side.
		jobsByStagedId = { ...jobsByStagedId, [stagedId]: { status: 'running', step: 'queued' } };
		const poll = async () => {
			try {
				const job = await get(fetch, `/ingestion-jobs/${jobId}`);
				jobsByStagedId = { ...jobsByStagedId, [stagedId]: job };
				if (job.status === 'done') {
					clearInterval(pollTimers[stagedId]);
					delete pollTimers[stagedId];
					toast('Ingested into the library.');
					await invalidateAll();
				} else if (job.status === 'error') {
					clearInterval(pollTimers[stagedId]);
					delete pollTimers[stagedId];
					toast(job.error_message ?? 'Ingestion failed.', 'alert');
				}
			} catch (err: any) {
				clearInterval(pollTimers[stagedId]);
				delete pollTimers[stagedId];
				toast(err.message, 'alert');
			}
		};
		poll();
		pollTimers[stagedId] = setInterval(poll, 2000);
	}

	for (const job of data.activeJobs ?? []) {
		jobsByStagedId = { ...jobsByStagedId, [job.staged_id]: job };
		watchJob(job.staged_id, job.id);
	}

	// Same leak fix as the admin Library page: without this, leaving the
	// page while a job is running leaves its 2s poll loop running forever.
	onDestroy(() => {
		for (const t of Object.values(pollTimers)) clearInterval(t);
	});

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

	function stagedFileUrl(item: any) {
		return `${PUBLIC_API_BASE}/api/staged/${item.id}/file#toolbar=0&navpanes=0&scrollbar=0`;
	}

	async function stageFile() {
		if (!selectedFile) return;
		staging = true;
		stageProgress = null;
		try {
			await chunkedUpload('/sources', selectedFile, {}, (p) => (stageProgress = p), 'stage');
			toast('Added to your staged list.');
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
			toast('Added to your staged list.');
			text = '';
			ingestOpen = false;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			staging = false;
		}
	}

	// Duplicate-on-ingest: _ingest_pages() (app/main.py) 409s with
	// duplicate_of when the staged body hashes to an already-ingested
	// document, rather than silently filing a second copy under a fresh
	// Reader-generated title/grade. Surfaced here so the practitioner can
	// choose to replace the old version or discard the redundant staged item.
	let duplicateStagedId = $state<string | null>(null);
	let duplicateOf = $state<string | null>(null);
	let duplicateMessage = $state('');
	let duplicateOpen = $state(false);

	async function ingestOne(id: string) {
		promotingId = id;
		try {
			const res = await post(fetch, `/staged/${id}/ingest`, {});
			watchJob(id, res.job_id);
		} catch (err: any) {
			const detail = err instanceof ApiError ? (err.detail as any) : null;
			if (err instanceof ApiError && err.status === 409 && detail?.duplicate_of) {
				duplicateStagedId = id;
				duplicateOf = detail.duplicate_of;
				duplicateMessage = detail.message;
				duplicateOpen = true;
			} else {
				toast(err.message, 'alert');
			}
		} finally {
			promotingId = null;
		}
	}

	async function replaceDuplicate() {
		if (!duplicateStagedId || !duplicateOf) return;
		const id = duplicateStagedId;
		const replaces = duplicateOf;
		duplicateOpen = false;
		promotingId = id;
		try {
			const res = await post(fetch, `/staged/${id}/ingest`, { replaces });
			watchJob(id, res.job_id);
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			promotingId = null;
		}
	}

	async function discardDuplicate() {
		if (!duplicateStagedId) return;
		const id = duplicateStagedId;
		duplicateOpen = false;
		await discardStaged(id);
	}

	async function discardStaged(id: string) {
		try {
			await del(fetch, `/staged/${id}`);
			toast('Discarded.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	// Same viewer as the admin Library page (web/src/routes/(admin)/admin/
	// +page.svelte) — library content is shared/admin-curated, and a
	// practitioner already reads it implicitly via their own consults and
	// per-source weighting below, so viewing it directly isn't new exposure
	// (app/auth.py's require_admin_or_practitioner backs both GET routes).
	let viewing = $state(false);
	let viewTitle = $state('');
	let viewLoading = $state(false);
	let viewBody = $state<{ body: string; body_reconstructed?: boolean } | null>(null);
	let viewOriginalUrl = $state<string | null>(null);

	async function viewDoc(s: any) {
		viewTitle = s.title;
		viewBody = null;
		viewOriginalUrl = null;
		viewing = true;
		if (s.original_name) {
			viewOriginalUrl = `${PUBLIC_API_BASE}/api/sources/${s.id}/original#toolbar=0&navpanes=0&scrollbar=0`;
			return;
		}
		viewLoading = true;
		try {
			viewBody = await get(fetch, `/sources/${s.id}/text`);
		} catch (err: any) {
			toast(err.message, 'alert');
			viewing = false;
		} finally {
			viewLoading = false;
		}
	}

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

<Spotlight title="Your knowledge weighting" actions={data.canUploadLibrary ? uploadActions : undefined}>
	<p class="hint">Boost or dampen how much each shared library source counts when your consults run.</p>

	{#if data.canUploadLibrary && data.staged?.length}
		<div class="staged">
			<strong>{data.staged.length} of your uploads not yet in the library</strong>
			<ul class="staged-list">
				{#each data.staged as item (item.id)}
					<li class="staged-item">
						<div class="staged-body">
							<div class="staged-title">
								{item.filename ?? 'Pasted text'}
								<Chip tone="neutral">{item.kind}</Chip>
								{#if item.page_count}<span class="hint">{item.page_count} page(s)</span>{/if}
							</div>
							<p class="staged-preview">{item.preview}{item.preview?.length >= 280 ? '…' : ''}</p>
							{#if jobsByStagedId[item.id] && jobsByStagedId[item.id].status !== 'error'}
								<div class="job-progress">
									<div class="track"><div class="fill" style="width: {jobProgressPercent(jobsByStagedId[item.id])}%"></div></div>
									<span class="hint">{jobLabel(jobsByStagedId[item.id])}</span>
								</div>
							{:else if jobsByStagedId[item.id]}
								<p class="hint job-error">{jobLabel(jobsByStagedId[item.id])}</p>
							{/if}
						</div>
						<div class="staged-actions">
							{#if item.kind === 'file'}
								<a class="view" href={stagedFileUrl(item)} target="_blank" rel="noopener">View</a>
							{/if}
							<button
								class="view"
								onclick={() => ingestOne(item.id)}
								disabled={promotingId === item.id || jobsByStagedId[item.id]?.status === 'running'}
							>
								{jobsByStagedId[item.id]?.status === 'running' ? 'Ingesting…' : 'Ingest'}
							</button>
							<button
							class="view danger"
							onclick={() => discardStaged(item.id)}
							disabled={jobsByStagedId[item.id]?.status === 'running'}
							title={jobsByStagedId[item.id]?.status === 'running' ? 'Ingestion is already running for this item' : undefined}
						>Discard</button>
						</div>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
	<input class="search" type="search" placeholder="Search by title…" bind:value={q} aria-label="Search library sources" />
	<DataTable
		columns={[{ key: 'title', label: 'Source', sortable: true }, { key: 'grade', label: 'Grade' }, { key: 'weight', label: 'Your weight' }, { key: 'actions', label: '' }]}
		rows={pageItems}
		empty="Nothing in the library yet."
	>
		{#snippet row(s)}
			<td>{s.title}</td>
			<td><Chip tone="neutral">grade {s.grade}</Chip></td>
			<td>
				<input type="number" min="0" max="5" value={s.weight} onchange={(e) => setWeight(s.id as string, Number((e.target as HTMLInputElement).value))} />
			</td>
			<td><button class="icon-btn" onclick={() => viewDoc(s)} title="View document" aria-label="View {s.title}"><Icon name="eye" /></button></td>
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

{#snippet uploadActions()}
	<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>
{/snippet}

<Dialog bind:open={ingestOpen} title="Add resources" wide>
	<Tabs bind:active={ingestTab} tabs={[{ id: 'upload', label: 'Upload a document' }, { id: 'text', label: 'Paste text' }]} />

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
					<embed src="{previewUrl}#toolbar=0&navpanes=0&scrollbar=0" type="application/pdf" class="pdf-preview" aria-label="{selectedFile.name} preview" />
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
		{/if}
	</div>
</Dialog>

<Dialog bind:open={duplicateOpen} title="Already in the library">
	<p>{duplicateMessage}</p>
	{#snippet footer()}
		<button class="view" onclick={() => (duplicateOpen = false)}>Cancel</button>
		<button class="view danger" onclick={discardDuplicate}>Discard staged item</button>
		<button class="view" onclick={replaceDuplicate}>Replace old version</button>
	{/snippet}
</Dialog>

<Dialog bind:open={viewing} title={viewTitle} wide>
	{#if viewOriginalUrl}
		<iframe class="doc-frame" src={viewOriginalUrl} title={viewTitle}></iframe>
	{:else if viewLoading}
		<p class="hint">Loading…</p>
	{:else if viewBody}
		{#if viewBody.body_reconstructed}
			<p class="hint">Rebuilt from passages — no original body was stored for this source.</p>
		{/if}
		<div class="doc-body">{viewBody.body}</div>
	{/if}
</Dialog>

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
	.icon-btn {
		display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
		border: 1px solid var(--line); background: var(--panel); color: var(--accent-ink);
		border-radius: var(--r); width: 2rem; height: 2rem; padding: 0;
		transition: background .15s var(--ease), border-color .15s var(--ease);
	}
	.icon-btn:hover { border-color: var(--accent); background: var(--accent-soft); }
	.doc-body { white-space: pre-wrap; font-size: var(--text-sm); line-height: 1.6; max-height: 60vh; overflow-y: auto; }
	.doc-frame { width: 100%; height: 75vh; border: none; border-radius: var(--r); }
	.pager button:disabled { opacity: .5; cursor: default; }
	.staged { display: grid; gap: var(--space-3); margin-bottom: var(--space-4); }
	.staged-list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-2); }
	.staged-item { display: flex; gap: var(--space-3); align-items: flex-start; padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--r); }
	.staged-body { flex: 1 1 auto; min-width: 0; }
	.staged-title { display: flex; align-items: center; gap: .4rem; font-weight: 650; flex-wrap: wrap; }
	.staged-preview { margin: .3rem 0 0; font-size: var(--text-sm); color: var(--muted); overflow-wrap: anywhere; }
	.staged-actions { display: flex; gap: .35rem; flex: 0 0 auto; flex-wrap: wrap; }
	.view {
		font: inherit; font-size: var(--text-sm); font-weight: 650; cursor: pointer;
		border: 1px solid var(--line); background: var(--panel); color: var(--accent-ink);
		border-radius: var(--r); padding: .3rem .7rem;
	}
	.view:hover { border-color: var(--accent); background: var(--accent-soft); }
	.view.danger { color: var(--danger); }
	.view.danger:hover { border-color: var(--danger); background: var(--danger-soft); }
	.view:disabled { opacity: .5; cursor: not-allowed; }
	.ingest { display: grid; gap: var(--space-3); }
	.ingest-panel { margin-top: var(--space-4); display: grid; gap: var(--space-3); }
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
	.upload-progress {
		display: flex; align-items: center; gap: var(--space-3);
		background: var(--panel-2); border-radius: 99px; padding: .35rem .35rem .35rem .1rem;
	}
	.upload-progress .bar { flex: 1 1 auto; height: 6px; border-radius: 99px; background: var(--accent); transition: width .2s var(--ease); margin-left: .25rem; }
	.upload-progress .hint { flex: 0 0 auto; padding-right: .5rem; white-space: nowrap; }
	.job-progress { margin-top: .4rem; display: grid; gap: .25rem; }
	.job-progress .track { height: 6px; border-radius: 99px; background: var(--panel-2); overflow: hidden; }
	.job-progress .fill { height: 100%; border-radius: 99px; background: var(--accent); transition: width .3s var(--ease); }
	.job-error { color: var(--danger); margin-top: .4rem; }
</style>
