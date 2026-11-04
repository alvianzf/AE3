<script lang="ts">
	import { onDestroy } from 'svelte';
	import { page as appPage } from '$app/state';
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { get, post, patch, put, del, ApiError } from '$lib/api';
	import { chunkedUpload } from '$lib/chunkedUpload';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Tabs from '$lib/components/Tabs.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import FolderTree, { type TreeNode } from '$lib/components/FolderTree.svelte';
	import GraphView, { type GraphNode, type GraphEdge } from '$lib/components/GraphView.svelte';
	import Menu from '$lib/components/Menu.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	let { data } = $props();

	// Graph maintenance: POST /api/relink and /api/consolidate existed with
	// no UI trigger anywhere — curl-only. Maintenance ops, not everyday
	// actions, so a confirm dialog first rather than a bare button.
	let maintenanceKind = $state<'relink' | 'consolidate' | null>(null);
	let maintenanceOpen = $state(false);
	let maintenanceRunning = $state(false);

	async function runMaintenance() {
		if (!maintenanceKind) return;
		const kind = maintenanceKind;
		maintenanceOpen = false;
		maintenanceRunning = true;
		try {
			const res = await post(fetch, `/${kind}`, {});
			toast(
				kind === 'relink'
					? `Linked ${res.linked?.length ?? 0} source(s), ${res.failed?.length ?? 0} failed.`
					: `Merged ${res.entity?.absorbed ?? 0} entit${res.entity?.absorbed === 1 ? 'y' : 'ies'}.`
			);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			maintenanceRunning = false;
		}
	}

	let ingestOpen = $state(false);
	let ingestTab = $state('upload');
	let mainTab = $state('library');
	let text = $state('');
	let fileInput = $state<HTMLInputElement>();
	let staging = $state(false);
	let stageProgress = $state<{ sent: number; total: number } | null>(null);

	// Staged items — uploaded/pasted, auto-enqueued for ingestion
	// immediately (specs/v6.12: no manual "Ingest" click or review-before-
	// committing step any more — a staged item IS the in-queue state,
	// shown as a progress card right in the Library grid, not a separate
	// tab). `data.staged` shrinks as each job finishes and its staged row
	// is deleted (app/main.py's _run_staged_ingest_job).
	let promotingId = $state<string | null>(null);

	// Ingestion jobs: promoting a staged item now returns a job id
	// immediately (app/main.py's POST /api/staged/{id}/ingest, backgrounded
	// via BackgroundTasks so a large document doesn't block behind nginx's
	// 300s proxy_read_timeout) instead of the finished document. Polled here
	// by staged_id so the staged item's own row can show live progress;
	// GET /api/ingestion-jobs/active on page load (+page.ts) re-populates
	// this from any job still running server-side, so progress survives a
	// reload instead of dying with the tab that started it.
	let jobsByStagedId = $state<Record<string, any>>({});
	const pollTimers: Record<string, ReturnType<typeof setInterval>> = {};

	// The just-ingested document, shown in the "Placed in library" dialog
	// right after a job finishes — the Reader already chose a folder and
	// tags at ingest time (app/ingestion/pipeline.py's suggested_folder /
	// topics), but nothing surfaced that choice to the admin before this;
	// the toast alone named the action, not the result.
	let placementPreview = $state<any | null>(null);
	// Document ids whose ingest just finished and haven't had their
	// Reader-suggested folder/tags/type reviewed yet — shown as a bell
	// icon on the card (specs/v6.12), dismissed by opening (or
	// explicitly skipping) the placement dialog. Per-browser only, not
	// persisted — a one-time nudge, not queue state (which is fully
	// server-side via ingestion_jobs/staged_sources already).
	let needsFinalization = $state<Set<string>>(new Set());
	function dismissFinalization(id: string) {
		needsFinalization = new Set([...needsFinalization].filter((x) => x !== id));
	}
	// setFolder/addTag/removeTag write through `data.sources` (invalidateAll),
	// not through placementPreview's own object reference — without this,
	// clicking a folder-suggestion chip or adding a tag moves/tags the
	// document but the open dialog keeps showing its stale pre-edit state.
	$effect(() => {
		if (!placementPreview) return;
		const fresh = (data.sources ?? []).find((x: any) => x.id === placementPreview.id);
		if (fresh && fresh !== placementPreview) placementPreview = fresh;
	});

	// A job occupies a staged item whether it's actually running or still
	// waiting for a concurrency slot (app/ingestion/queue.py) — either
	// way, re-ingesting or discarding that same item from under it is
	// blocked the same as before, not just while status='running'.
	function jobActive(job: any): boolean {
		return job?.status === 'running' || job?.status === 'queued';
	}

	function jobLabel(job: any): string {
		if (job.status === 'error') return `Failed: ${job.error_message ?? 'unknown error'}`;
		// Genuinely waiting for a concurrency slot (app/ingestion/
		// queue.py), distinct from step='queued' below (already picked
		// up, just hasn't reported its first real progress update yet) —
		// found live, 2026-11-03: an unbounded number of simultaneous
		// ingests was itself enough to OOM the app (DEPLOY.md).
		if (job.status === 'queued') return 'Waiting in queue…';
		switch (job.step) {
			case 'queued': return 'Starting…';
			case 'reading': return 'Reading document…';
			case 'chunking': return 'Splitting into passages…';
			case 'embedding': return 'Embedding chunks…';
			case 'extracting_graph': return `Extracting knowledge graph (${job.step_detail ?? '…'})…`;
			case 'writing': return 'Writing to library…';
			default: return 'Ingesting…';
		}
	}

	// Rough, not exact: the pipeline's stages aren't equal-cost (reading is
	// one LLM call, extracting_graph can be dozens), but a single ordered
	// list is all the backend reports, so each stage gets an equal slice of
	// the bar and extracting_graph — the one stage with a real counter
	// (step_detail = "N of M passages") — interpolates within its own slice
	// from that counter rather than jumping in one step like the rest.
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

	function formatEta(seconds: number | null | undefined): string {
		if (seconds == null) return '';
		if (seconds < 60) return `~${Math.max(1, Math.round(seconds))}s`;
		const mins = Math.round(seconds / 60);
		return mins < 60 ? `~${mins}m` : `~${Math.round(mins / 60)}h`;
	}

	function formatChars(n: number): string {
		return n >= 1000 ? `~${Math.round(n / 1000)}k chars` : `${n} chars`;
	}

	function watchJob(stagedId: string, jobId: string) {
		if (pollTimers[stagedId]) clearInterval(pollTimers[stagedId]);
		// Set synchronously, before the first poll's network round-trip
		// resolves — without this, ingestOne's `finally` clears promotingId
		// right after calling watchJob, leaving a window (until the first
		// GET /ingestion-jobs/{id} response lands) where the Ingest button
		// is neither disabled nor labeled "Ingesting…", even though a job is
		// already running server-side (found in review: fast enough to
		// double-click and start two jobs for the same staged item).
		jobsByStagedId = { ...jobsByStagedId, [stagedId]: { status: 'running', step: 'queued' } };
		const poll = async () => {
			try {
				const job = await get(fetch, `/ingestion-jobs/${jobId}`);
				jobsByStagedId = { ...jobsByStagedId, [stagedId]: job };
				if (job.status === 'done') {
					clearInterval(pollTimers[stagedId]);
					delete pollTimers[stagedId];
					clearFiltersAfterIngest();
					await invalidateAll();
					const placed = (data.sources ?? []).find((x: any) => x.id === job.result_document_id);
					toast(
						placed
							? `"${placed.title.slice(0, 40)}" ingested — filed in ${placed.folder_path || '(root)'}.`
							: 'Ingested into the library.'
					);
					// A bell icon on the card, not an auto-opened dialog
					// (specs/v6.12) — with auto-ingest-on-upload, a finished
					// job isn't necessarily something the admin is watching
					// for any more; popping a dialog over whatever else
					// they're doing is the wrong interruption now that
					// uploads queue up unattended.
					if (placed) needsFinalization = new Set([...needsFinalization, placed.id]);
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

	// Resume progress for anything still running server-side — the actual
	// "survives a page reload" requirement, not just an in-memory poll.
	for (const job of data.activeJobs ?? []) {
		jobsByStagedId = { ...jobsByStagedId, [job.staged_id]: job };
		watchJob(job.staged_id, job.id);
	}
	// Every staged item now carries its latest job's status (app/
	// core_store.py's list_staged_sources LATERAL join) — an errored one
	// (job_status='error') shows that error without polling (no active
	// job to poll); one with job_status=null never actually got a job at
	// all (specs/v6.12: pre-dates auto-ingest-on-stage, or a request that
	// failed between staging and the auto-ingest call) and is kicked off
	// here instead of sitting stuck forever with nothing to start it.
	for (const item of data.staged ?? []) {
		if (jobsByStagedId[item.id]) continue;
		if (item.job_status === 'error') {
			jobsByStagedId = {
				...jobsByStagedId,
				[item.id]: { status: 'error', step: 'error', error_message: item.job_error_message }
			};
		} else if (!item.job_status) {
			ingestOne(item.id);
		}
	}

	// Nothing else clears these on navigation — without this, leaving the
	// page while a job is running leaves its 2s poll loop running forever
	// (found in review), still hitting the API and updating state on a
	// component instance the user no longer sees.
	onDestroy(() => {
		for (const t of Object.values(pollTimers)) clearInterval(t);
	});

	// Status bar counts/ETA (specs/v6.12) — refreshed on its own interval
	// rather than piggybacking on watchJob's per-item 2s poll, since this
	// has to stay correct even when this browser isn't watching any job
	// at all (another admin's upload, a different device).
	let queueStats = $state(data.queueStats);
	const statsInterval = setInterval(async () => {
		try { queueStats = await get(fetch, '/ingestion-jobs/stats'); } catch {}
	}, 5000);
	onDestroy(() => clearInterval(statsInterval));

	function stagedFileUrl(item: any) {
		// #toolbar=0&navpanes=0: no PDF-viewer chrome/sidebar on this preview either.
		return `${PUBLIC_API_BASE}/api/staged/${item.id}/file#toolbar=0&navpanes=0&scrollbar=0`;
	}

	// Library browser: categories = topics (from /api/coverage, with counts),
	// a kind filter alongside them, and a search box over both. Filtered
	// client-side since the PoC library tops out around a few dozen sources
	// (README "Deliberate PoC limits") and +page.ts already loads up to 200.
	let q = $state('');
	let activeTopic = $state('');
	// Icons (the original card grid) / list (same cards, one per row) /
	// table (a compact Explorer-style "Details" view with its own
	// columns) — the three view modes any desktop file browser offers.
	// Persisted locally only (per-browser convenience, not server state).
	let viewMode = $state<'icons' | 'list' | 'table'>(
		(typeof localStorage !== 'undefined' && (localStorage.getItem('admin-library-view') as any)) || 'icons'
	);
	$effect(() => {
		try { localStorage.setItem('admin-library-view', viewMode); } catch {}
	});

	// Sort — file name or date ingested, each ascending/descending. Not
	// "date uploaded" as a third, separate option: checked the data
	// model first (found live, "sort by... date uploaded" asked) — a
	// Document only ever persists one timestamp (ingested_at/
	// created_at, the same value under both names at the API boundary).
	// The staged item's own upload-time row is deleted the moment
	// promotion succeeds, so there's no second, distinct "uploaded at"
	// moment surviving anywhere to sort by — a document's upload and
	// ingest timestamps are the same thing in this system (doubly true
	// since v6.12's auto-ingest-on-upload removed any real gap between
	// the two events anyway). Persisted locally, same as viewMode.
	let sortBy = $state<'title' | 'created_at'>(
		(typeof localStorage !== 'undefined' && (localStorage.getItem('admin-library-sort') as any)) || 'title'
	);
	let sortDir = $state<'asc' | 'desc'>(
		(typeof localStorage !== 'undefined' && (localStorage.getItem('admin-library-sort-dir') as any)) || 'asc'
	);
	$effect(() => {
		try {
			localStorage.setItem('admin-library-sort', sortBy);
			localStorage.setItem('admin-library-sort-dir', sortDir);
		} catch {}
	});
	function sortDocs(docs: any[]): any[] {
		const dir = sortDir === 'asc' ? 1 : -1;
		return [...docs].sort((a, b) => {
			if (sortBy === 'title') return a.title.localeCompare(b.title) * dir;
			return ((a.created_at ?? '') < (b.created_at ?? '') ? -1 : (a.created_at ?? '') > (b.created_at ?? '') ? 1 : 0) * dir;
		});
	}
	// The folder currently being browsed — a real Finder/Nautilus-style
	// "current directory", not a filter chip: '' is root. Navigating into
	// a folder shows exactly its direct contents (subfolders + the
	// documents filed there), not every descendant flattened into one
	// list — that's what folders of a real file browser mean. Deep-linked
	// from a source's own detail page, e.g. "/admin/[id]"'s folder
	// breadcrumb (specs/v6.8/01/02) — lands already browsing that folder.
	let currentPath = $state(appPage.url.searchParams.get('folder') ?? '');

	// A real nested tree, not a flat chip row — folders still have no
	// node of their own (specs/v6.8/01's string-prefix model), so this is
	// built client-side from the already-loaded source list's folder_path
	// values, same PoC-scale reasoning the rest of this page's filtering
	// already runs on, not from a dedicated coverage-style endpoint.
	const folderTree = $derived.by(() => {
		const index = new Map<string, TreeNode>();
		const roots: TreeNode[] = [];
		function ensure(acc: string, seg: string): TreeNode {
			let node = index.get(acc);
			if (!node) {
				node = { name: seg, path: acc, count: 0, children: [], docs: [] };
				index.set(acc, node);
				(acc.includes('/') ? ensure(acc.slice(0, acc.lastIndexOf('/')), '').children : roots).push(node);
			}
			return node;
		}
		for (const s of data.sources ?? []) {
			const path = s.folder_path || '';
			if (!path) continue;
			let acc = '';
			for (const seg of path.split('/')) {
				acc = acc ? `${acc}/${seg}` : seg;
				ensure(acc, seg).count++;
			}
			// The tree-view tab's leaf rows (specs/v6.8/01's Finder-copy
			// request) — a document belongs to the deepest node on its own
			// path, not every ancestor, so this is outside the count++ loop
			// above (which deliberately does touch every ancestor, for the
			// tile/sidebar counts elsewhere on this page).
			index.get(path)?.docs.push(s);
		}
		// Explicitly-created folders (specs/v6.8/01's empty-folder
		// addendum) appear in the tree even with zero documents — same
		// ensure() walk, just without the count++ a document triggers.
		for (const path of data.folders ?? []) {
			let acc = '';
			for (const seg of path.split('/')) {
				acc = acc ? `${acc}/${seg}` : seg;
				ensure(acc, seg);
			}
		}
		function sortTree(nodes: TreeNode[]) {
			nodes.sort((a, b) => a.name.localeCompare(b.name));
			for (const n of nodes) { n.docs = sortDocs(n.docs); sortTree(n.children); }
		}
		sortTree(roots);
		return roots;
	});
	// Root-level documents (no folder) — the tree-view tab's top-level
	// leaf rows, alongside the top-level folder nodes above.
	const rootDocs = $derived(sortDocs((data.sources ?? []).filter((s: any) => !s.folder_path)));

	// specs/v8 §7.4 — Graph view rebuilt on <canvas> (GraphView.svelte),
	// re-added as a third tab alongside Library/Tree view. Concepts only
	// now — the document/folder layer the original two-layer version also
	// offered is redundant with the Tree view tab right next to it, and
	// dropping it is one less thing to keep light. A real network call
	// (the knowledge graph lives in Neo4j, not anything already loaded
	// here), so it only runs once the admin actually opens this tab.
	let conceptGraph = $state<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
	let conceptGraphLoading = $state(false);
	$effect(() => {
		if (mainTab === 'graph') loadConceptGraph();
	});
	async function loadConceptGraph() {
		if (conceptGraph || conceptGraphLoading) return;
		conceptGraphLoading = true;
		try {
			const res = await get(fetch, '/graph/concepts');
			conceptGraph = {
				nodes: (res.nodes ?? []).map((n: any) => ({
					id: n.id, label: n.name, group: n.type, size: 3 + Math.min(7, Math.sqrt(n.mentions ?? 1))
				})),
				edges: (res.edges ?? []).map((e: any) => ({ source: e.source, target: e.target, label: e.rel_type }))
			};
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			conceptGraphLoading = false;
		}
	}
	// Graph view (specs/v6.13) — two switchable layers in one tab.
	// Every known folder path, flat and including subfolders at every
	// depth — the "Move to..." dialog's quick-pick suggestions, so moving
	// a document doesn't require typing out a deep path by hand.
	const folderPaths = $derived.by(() => {
		const paths: string[] = [];
		function walk(nodes: TreeNode[]) {
			for (const n of nodes) { paths.push(n.path); walk(n.children); }
		}
		walk(folderTree);
		return paths.sort();
	});

	function findNode(nodes: TreeNode[], path: string): TreeNode | null {
		for (const n of nodes) {
			if (n.path === path) return n;
			if (path === n.path || path.startsWith(`${n.path}/`)) {
				const hit = findNode(n.children, path);
				if (hit) return hit;
			}
		}
		return null;
	}

	// The subfolder tiles shown in the main pane for whatever folder is
	// currently open — direct children only (findNode().children), same
	// "one level, not every descendant" rule the documents below follow.
	const visibleSubfolders = $derived.by(() => {
		if (!currentPath) return folderTree;
		return findNode(folderTree, currentPath)?.children ?? [];
	});

	const breadcrumb = $derived.by(() => {
		if (!currentPath) return [];
		const segments = currentPath.split('/');
		let acc = '';
		return segments.map((name) => {
			acc = acc ? `${acc}/${name}` : name;
			return { name, path: acc };
		});
	});

	// A non-empty search box switches to a flat, library-wide result list
	// (every matching document regardless of which folder it's in) — the
	// same "search this folder vs. search everywhere" split Finder/
	// Nautilus both make, just defaulting to "everywhere" once you've
	// typed something, since not knowing which folder a document is in
	// is exactly why you'd search for it.
	const searching = $derived(q.trim().length > 0);

	const filtered = $derived.by(() => {
		const needle = q.trim().toLowerCase();
		const matches = (data.sources ?? []).filter((s: any) => {
			if (activeTopic && !(s.topics ?? []).includes(activeTopic)) return false;
			if (searching) {
				// Omni search: every field a document has, not just a fixed
				// subset — folder path and tags included, so typing a folder
				// name or a tag surfaces its documents the same as a title
				// or summary match would.
				const haystack = [s.title, s.summary, s.origin, s.author, s.filename, s.folder_path, s.kind, ...(s.topics ?? [])];
				return haystack.some((v) => (v ?? '').toLowerCase().includes(needle));
			}
			return (s.folder_path || '') === currentPath;
		});
		return sortDocs(matches);
	});

	// Paginated client-side too, same reasoning as the filtering above — the
	// full (filtered) set is already in memory, no reason to round-trip the
	// server for a page change. `page` un-clamped in state, clamped only at
	// read time so a filter that shrinks the result set can't strand it past
	// the new last page.
	const DOCS_PER_PAGE = 12;
	let page = $state(1);
	const totalPages = $derived(Math.max(1, Math.ceil(filtered.length / DOCS_PER_PAGE)));
	const shownPage = $derived(Math.min(page, totalPages));
	const pageItems = $derived.by(() => {
		const start = (shownPage - 1) * DOCS_PER_PAGE;
		return filtered.slice(start, start + DOCS_PER_PAGE);
	});

	// Regrade/delete: PATCH and DELETE /api/sources/{id} always existed on the
	// backend (the pre-rewrite admin page used both, static/app.js) but had no
	// UI in this rewrite — README.md's "a source can be corrected or removed"
	// had no way to do either (specs/v4/04-known-issues.md#h1).
	// Tags (topics) are editable/assignable by an admin — the Reader's
	// suggestion at ingest is only a starting point, same relationship
	// grade/folder already have to their own Reader suggestions.
	let newTagText: Record<string, string> = $state({});

	async function setTopics(s: any, topics: string[]) {
		try {
			await patch(fetch, `/sources/${s.id}/topics`, { topics });
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	function addTag(s: any) {
		const raw = (newTagText[s.id] ?? '').trim();
		if (!raw) return;
		newTagText = { ...newTagText, [s.id]: '' };
		if ((s.topics ?? []).includes(raw.toLowerCase())) return;
		setTopics(s, [...(s.topics ?? []), raw]);
	}

	function removeTag(s: any, tag: string) {
		setTopics(s, (s.topics ?? []).filter((t: string) => t !== tag));
	}

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

	// Drag a doc card or a folder tile onto a folder (tree node, main-pane
	// tile, or breadcrumb segment) to move it — a document drag reuses
	// setFolder() (the same write the inline per-card field already
	// triggers); a folder drag reuses moveFolderTo() (the same write the
	// rename dialog already triggers) with its own name appended under
	// the drop target, i.e. nesting it there.
	let draggedId = $state<string | null>(null);
	let draggedFolderPath = $state<string | null>(null);

	function handleDropOnFolder(targetPath: string) {
		if (draggedId) {
			const s = (data.sources ?? []).find((x: any) => x.id === draggedId);
			draggedId = null;
			if (s) setFolder(s, targetPath);
			return;
		}
		if (draggedFolderPath) {
			const source = draggedFolderPath;
			draggedFolderPath = null;
			if (targetPath === source || targetPath.startsWith(`${source}/`)) {
				toast("Can't move a folder into itself or its own subfolder.", 'alert');
				return;
			}
			const name = source.split('/').pop()!;
			const dest = targetPath ? `${targetPath}/${name}` : name;
			if (dest === source) return;
			moveFolderTo(source, dest);
		}
	}

	// A source's folder is always the admin's call (specs/v6.8/01) — the
	// Reader's suggested_folder only sets the starting value at ingest
	// time, same relationship suggested_grade already has to grade above.
	async function setFolder(s: any, folderPath: string) {
		const next = folderPath.trim();
		if (next === (s.folder_path || '')) return;
		try {
			await patch(fetch, `/sources/${s.id}/folder`, { folder_path: next });
			toast(`"${s.title.slice(0, 40)}" moved to ${next || '(root)'}.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	// Content-type classification (article/book/presentation/protocol/
	// etc.) — an admin's call always wins over the Reader's own
	// suggestion at ingest time, same relationship folder/grade/topics
	// already have to their own Reader suggestions.
	const DOC_TYPES = [
		'article', 'book', 'presentation', 'education material',
		'lecture notes', 'protocol', 'picture', 'chart', 'other'
	];
	async function setDocType(s: any, docType: string) {
		if (docType === (s.doc_type ?? '')) return;
		try {
			await patch(fetch, `/sources/${s.id}/doc-type`, { doc_type: docType });
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	// "Move to..." — reachable by right-click on a document card or its
	// explicit Move button, not just drag-and-drop (not every input
	// device supports drag, and a target folder deep in the tree may not
	// even be visible/expanded to drop onto).
	let movingSource = $state<any>(null);
	let movingOpen = $state(false);
	let movingPath = $state('');

	function askMove(s: any) {
		movingSource = s;
		movingPath = s.folder_path ?? '';
		movingOpen = true;
	}

	function onDocContextMenu(e: MouseEvent, s: any) {
		e.preventDefault();
		askMove(s);
	}

	async function confirmMove(e: Event) {
		e.preventDefault();
		if (!movingSource) return;
		await setFolder(movingSource, movingPath);
		movingOpen = false;
	}

	let renamingFolder = $state(false);
	let renameOldPath = $state('');
	let renameNewPath = $state('');
	let renamingSubmitting = $state(false);

	function askRenameFolder(folderPath: string) {
		renameOldPath = folderPath;
		renameNewPath = folderPath;
		renamingFolder = true;
	}

	async function moveFolderTo(oldPath: string, newPath: string) {
		try {
			const result = await post(fetch, '/library/folders/rename', {
				old_path: oldPath, new_path: newPath
			});
			toast(`Moved ${result.moved} source${result.moved === 1 ? '' : 's'} to "${newPath || '(root)'}".`);
			if (currentPath === oldPath) currentPath = newPath;
			else if (currentPath.startsWith(`${oldPath}/`)) {
				// Drop oldPath AND its following slash before re-prefixing
				// with newPath — found in review: when newPath is '' (moved
				// to root), the old `newPath + currentPath.slice(oldPath.
				// length)` kept that slash (slice(oldPath.length) includes
				// it), producing a currentPath like "/B/C" that no real
				// folder_path value ever has, so nothing in the library
				// matched it until the admin manually navigated away.
				const suffix = currentPath.slice(oldPath.length + 1);
				currentPath = newPath ? `${newPath}/${suffix}` : suffix;
			}
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function renameFolder(e: Event) {
		e.preventDefault();
		if (!renameOldPath) return; // the root folder can't be renamed
		renamingSubmitting = true;
		try {
			await moveFolderTo(renameOldPath, renameNewPath);
			renamingFolder = false;
		} finally {
			renamingSubmitting = false;
		}
	}

	// A folder created ahead of any document landing in it (specs/
	// v6.8/01's empty-folder addendum) — always created under the
	// currently-open folder, same as a real file browser's "New Folder"
	// always being a subfolder of whatever directory you're looking at.
	let newFolderOpen = $state(false);
	let newFolderName = $state('');
	let newFolderSubmitting = $state(false);

	async function createFolder(e: Event) {
		e.preventDefault();
		const name = newFolderName.trim();
		if (!name) return;
		newFolderSubmitting = true;
		try {
			const path = currentPath ? `${currentPath}/${name}` : name;
			await post(fetch, '/library/folders', { folder_path: path });
			toast(`Created "${path}".`);
			newFolderOpen = false;
			newFolderName = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			newFolderSubmitting = false;
		}
	}

	let deletingFolder = $state<{ path: string; count: number } | null>(null);
	let deletingFolderOpen = $state(false);
	let deletingFolderSubmitting = $state(false);

	function askDeleteFolder(path: string, count: number) {
		deletingFolder = { path, count };
		deletingFolderOpen = true;
	}

	async function confirmDeleteFolder() {
		if (!deletingFolder) return;
		const { path } = deletingFolder;
		deletingFolderSubmitting = true;
		try {
			const result = await post(fetch, '/library/folders/delete', { folder_path: path });
			toast(`Deleted "${path}" (${result.deleted_documents} document${result.deleted_documents === 1 ? '' : 's'}).`);
			deletingFolderOpen = false;
			if (currentPath === path || currentPath.startsWith(`${path}/`)) {
				currentPath = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';
			}
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			deletingFolderSubmitting = false;
		}
	}

	// Private knowledge base (specs/v6.9/01) — a second, independent
	// selection set over the already-ingested doc-grid, not a reuse of
	// `selected` above (that one's scoped to the staged-upload queue).
	let librarySelected = $state<Set<string>>(new Set());

	function toggleLibrarySelected(id: string) {
		const next = new Set(librarySelected);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		librarySelected = next;
	}

	async function setPrivate(s: any, isPrivate: boolean) {
		try {
			await patch(fetch, `/sources/${s.id}/privacy`, { is_private: isPrivate });
			toast(`"${s.title.slice(0, 40)}" is now ${isPrivate ? 'private' : 'public'}.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function setPrivateBulk(isPrivate: boolean) {
		const ids = [...librarySelected];
		if (!ids.length) return;
		try {
			await Promise.all(ids.map((id) => patch(fetch, `/sources/${id}/privacy`, { is_private: isPrivate })));
			toast(`${ids.length} source${ids.length === 1 ? '' : 's'} set to ${isPrivate ? 'private' : 'public'}.`);
			librarySelected = new Set();
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function setFolderPrivate(folderPath: string, isPrivate: boolean) {
		try {
			const result = await post(fetch, '/library/folders/privacy', { folder_path: folderPath, is_private: isPrivate });
			toast(`${result.updated} source${result.updated === 1 ? '' : 's'} in "${folderPath}" set to ${isPrivate ? 'private' : 'public'}.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	// Who specifically can still see a private document — a separate
	// action from the privacy toggle itself, reachable again later, not
	// frozen at the moment it was privatized (specs/v6.9/01).
	let accessEditing = $state<any>(null);
	let accessOpen = $state(false);
	let accessSelected = $state<Set<string>>(new Set());
	let accessSubmitting = $state(false);

	async function askAccess(s: any) {
		accessEditing = s;
		accessOpen = true;
		accessSelected = new Set();
		try {
			const ids: string[] = await get(fetch, `/sources/${s.id}/access`);
			accessSelected = new Set(ids);
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	function toggleAccessSelected(id: string) {
		const next = new Set(accessSelected);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		accessSelected = next;
	}

	async function saveAccess() {
		if (!accessEditing) return;
		accessSubmitting = true;
		try {
			await put(fetch, `/sources/${accessEditing.id}/access`, { practitioner_ids: [...accessSelected] });
			toast('Access updated.');
			accessOpen = false;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			accessSubmitting = false;
		}
	}

	// Claim/assign an uploader — specifically for documents ingested
	// before v6.11 (uploaded_by is captured automatically for anything
	// after). No real history to prefill from: the audit log's "ingest"
	// events all carry the literal actor="admin", never a real per-user
	// identity (checked live, 2026-11-04) — so this is a plain admin
	// override, not a pick-from-a-list of known candidates.
	let uploadedByEditing = $state<any>(null);
	let uploadedByOpen = $state(false);
	let uploadedByValue = $state('');
	function askAssignUploader(s: any) {
		uploadedByEditing = s;
		uploadedByValue = s.uploaded_by ?? '';
		uploadedByOpen = true;
	}
	async function confirmAssignUploader(e: Event) {
		e.preventDefault();
		if (!uploadedByEditing) return;
		try {
			await patch(fetch, `/sources/${uploadedByEditing.id}/uploaded-by`, { uploaded_by: uploadedByValue });
			uploadedByOpen = false;
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
			// chunkedUpload.ts). 'stage' (reads/stores the file, no Reader
			// call yet) then ingestOne() right below auto-queues it —
			// specs/v6.12: no separate staged-review step any more, the
			// card shows up with a progress bar immediately.
			const staged = await chunkedUpload('/sources', selectedFile, {}, (p) => (stageProgress = p), 'stage');
			pickFile(null);
			if (fileInput) fileInput.value = '';
			ingestOpen = false;
			await invalidateAll();
			if (staged?.id) ingestOne(staged.id);
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
			const staged = await res.json();
			text = '';
			ingestOpen = false;
			await invalidateAll();
			if (staged?.id) ingestOne(staged.id);
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
			const staged = await post(fetch, '/scrape', { url: url.trim() });
			url = '';
			ingestOpen = false;
			await invalidateAll();
			if (staged?.id) ingestOne(staged.id);
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			scraping = false;
		}
	}

	function clearFiltersAfterIngest() {
		// An active category filter could otherwise hide a source that
		// was just ingested, with nothing telling the admin why it isn't
		// in the list (specs/v4/04-known-issues.md#m16, found in this
		// page's own initial review).
		q = activeTopic = '';
	}

	// Duplicate-on-ingest: _ingest_pages() (app/main.py) 409s with
	// duplicate_of when the staged body hashes to an already-ingested
	// document, rather than silently filing a second copy under a fresh
	// Reader-generated title/grade. Surfaced here instead of a plain toast
	// so the admin can choose to replace the old version or discard the
	// redundant staged item.
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

	// "Retry all" — every staged item currently sitting in status='error'
	// (an interrupted/failed job, e.g. the Nebius billing exhaustion that
	// produced a real 15-item backlog, 2026-11-03), retried one call each
	// rather than a dedicated bulk endpoint — there's no batch-retry
	// route and reusing ingestOne() per id keeps this consistent with
	// the single-item Retry button right next to it.
	let retryingAll = $state(false);
	const erroredStagedIds = $derived(
		(data.staged ?? [])
			.filter((item: any) => jobsByStagedId[item.id]?.status === 'error')
			.map((item: any) => item.id)
	);
	async function retryAll() {
		const ids = erroredStagedIds;
		if (!ids.length) return;
		retryingAll = true;
		try {
			// Sequential, not Promise.all — ingestOne() writes to shared
			// state (promotingId, and the duplicateStagedId/duplicateOf/
			// duplicateMessage/duplicateOpen quartet for a 409). Running
			// several concurrently let one duplicate's dialog silently
			// clobber another's before the admin ever saw it (found in
			// review). Sequential alone isn't quite enough either —
			// ingestOne() doesn't block on the dialog being resolved, it
			// just opens it and returns — so also stop the batch the
			// moment one opens, instead of racing straight into the next
			// item's dialog too. Whatever's left over is still 'error'
			// and picked up by the next Retry all (or individually).
			for (const id of ids) {
				await ingestOne(id);
				if (duplicateOpen) break;
			}
		} finally {
			retryingAll = false;
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
</script>

<svelte:head><title>Knowledge — Admin portal</title></svelte:head>

<!-- specs/v4/03: library list stays Tier 1 (the actual work surface).
     Teaching Clinic (upload/paste/scrape) is an on-demand modal reached via
     the library's "+ Add resources" action; audit history and graph stats
     each moved to their own page (removed from here outright, not just
     de-weighted) rather than sitting in a rail panel next to the library. -->
<Spotlight title="Knowledge library" actions={libraryActions}>
	<Tabs
		bind:active={mainTab}
		tabs={[
			{ id: 'library', label: 'Library' },
			{ id: 'tree', label: 'Tree view' },
			{ id: 'graph', label: 'Graph view' }
		]}
	/>

	<div class="tab-panel">
	{#if mainTab === 'library'}
		{#if (data.staged?.length ?? 0) > 0 || (queueStats?.queued_count ?? 0) > 0 || (queueStats?.processing_count ?? 0) > 0}
			<div class="queue-status-row">
				<p class="queue-status hint">
					{data.sources.length} ingested
					· {(queueStats?.queued_count ?? 0) + (queueStats?.processing_count ?? 0)} in queue
					{#if queueStats?.processing_count}({queueStats.processing_count} processing){/if}
					{#if queueStats?.total_queued_chars}· {formatChars(queueStats.total_queued_chars)} queued{/if}
					{#if queueStats?.estimated_seconds_remaining != null}· est. {formatEta(queueStats.estimated_seconds_remaining)} remaining{/if}
				</p>
				{#if erroredStagedIds.length}
					<Button variant="outlined" onclick={retryAll} loading={retryingAll}>
						Retry all ({erroredStagedIds.length})
					</Button>
				{/if}
			</div>
		{/if}
		<div class="search-bar">
			<div class="search-input-wrap">
				<input
					class="search"
					type="search"
					placeholder="Search titles, summaries, origins, authors, folders, tags…"
					bind:value={q}
					oninput={() => (page = 1)}
					aria-label="Search the library"
				/>
				{#if q}
					<button class="search-clear" onclick={() => { q = ''; page = 1; }} aria-label="Clear search">&times;</button>
				{/if}
			</div>
			<div class="sort-control">
				<select bind:value={sortBy} aria-label="Sort by">
					<option value="title">Name</option>
					<option value="created_at">Date ingested</option>
				</select>
				<button
					class="sort-dir"
					class:desc={sortDir === 'desc'}
					onclick={() => (sortDir = sortDir === 'asc' ? 'desc' : 'asc')}
					title={sortDir === 'asc' ? 'Ascending' : 'Descending'}
					aria-label={sortDir === 'asc' ? 'Sort ascending' : 'Sort descending'}
				>
					<Icon name="chevron" size={13} />
				</button>
			</div>
			<div class="view-toggle" role="group" aria-label="Document view">
				<button class:active={viewMode === 'icons'} onclick={() => (viewMode = 'icons')} title="Icons" aria-label="Icons view"><Icon name="grid" size={15} /></button>
				<button class:active={viewMode === 'list'} onclick={() => (viewMode = 'list')} title="List" aria-label="List view"><Icon name="list" size={15} /></button>
				<button class:active={viewMode === 'table'} onclick={() => (viewMode = 'table')} title="Columns" aria-label="Columns view"><Icon name="table" size={15} /></button>
			</div>
		</div>

		{#if data.graph}
			<!-- Found live ("why does the library have 0 concepts?"): this
			     always read .concepts, a field store.graph_stats() (app/
			     graph/store.py) never actually returns — its real key is
			     "entities". The stat was silently always 0 since whenever
			     this line was first written, not something this session's
			     work broke. -->
			<p class="hint graph-stats">{data.graph.entities ?? 0} concepts · {data.graph.mentions ?? 0} links · {(data.graph.unlinked ?? []).length} unlinked sources</p>
		{/if}

		<!-- DMOZ-style categories: one scrollable row, always visible above the
		     documents — https://dmoz-odp.com/'s shape, but a single x-scroll
		     strip instead of a wrapping grid so a tile stays short (a
		     name-and-count pill) no matter how many categories there are.
		     Topic is the only hierarchy the graph actually has (Neo4j has no
		     subcategory nodes), so Kind below is a facet, not a second real
		     tier — an honest read of a flat data model, not a fake nesting. -->
		<div class="directory-row">
			<button class="dir-tile" class:active={!activeTopic} onclick={() => { activeTopic = ''; page = 1; }}>
				<span class="dir-name">All</span>
				<span class="dir-count">{data.sources.length}</span>
			</button>
			{#each data.coverage as c (c.topic)}
				<button class="dir-tile" class:active={activeTopic === c.topic} onclick={() => { activeTopic = activeTopic === c.topic ? '' : c.topic; page = 1; }}>
					<span class="dir-name">{c.topic}</span>
					<span class="dir-count">{c.sources}</span>
				</button>
			{/each}
		</div>
		{#if !data.coverage.length}
			<!-- specs/v7/03 — the grid's own EmptyState just below already
			     covers the identical "truly nothing ingested" condition
			     with the full icon/headline/CTA treatment; this row stays a
			     plain hint rather than a second, redundant copy of the
			     same "start here" block stacked right above it. -->
			<p class="hint">Nothing ingested yet — use "+ Add resources" to start teaching Clinic.</p>
		{/if}

		<div class="library-layout">
			<!-- A real folder tree for quick-jump navigation (specs/v6.8/01) —
			     click a folder to open it (same as double-clicking its tile in
			     the main pane), drag a doc card or another folder tile onto one
			     to move it there, hover for rename/privatize. -->
			<aside class="folder-sidebar">
				<div
					class="node root-node"
					class:active={!currentPath}
					ondragover={(e) => e.preventDefault()}
					ondrop={(e) => { e.preventDefault(); handleDropOnFolder(''); }}
				>
					<button class="name" onclick={() => { currentPath = ''; page = 1; }}>
						<Icon name="folder" size={13} /> Library <span class="count">{data.sources.length}</span>
					</button>
				</div>
				<FolderTree
					nodes={folderTree}
					activePath={currentPath}
					onSelect={(path) => { currentPath = path; page = 1; }}
					onDrop={handleDropOnFolder}
					onRename={askRenameFolder}
					onPrivatize={setFolderPrivate}
					onDelete={(path, count) => askDeleteFolder(path, count)}
				/>
			</aside>

			<div class="library-main">
				{#if !searching}
					<!-- Finder/Nautilus-style breadcrumb — "Library" is root,
					     each segment is a real folder_path prefix you can jump
					     back up to. -->
					<div class="breadcrumb-row">
						<nav class="breadcrumb" aria-label="Folder path">
							<button onclick={() => { currentPath = ''; page = 1; }} disabled={!currentPath}>Library</button>
							{#each breadcrumb as crumb, i (crumb.path)}
								<span class="sep">/</span>
								<button
									onclick={() => { currentPath = crumb.path; page = 1; }}
									disabled={i === breadcrumb.length - 1}
								>{crumb.name}</button>
							{/each}
						</nav>
						<Button variant="text" onclick={() => { newFolderName = ''; newFolderOpen = true; }}>
							<Icon name="folder" size={13} />+ New folder
						</Button>
					</div>
				{/if}

				{#if librarySelected.size}
					<div class="bulk-bar">
						<span class="hint">{librarySelected.size} selected</span>
						<Button variant="outlined" onclick={() => setPrivateBulk(true)}><Icon name="lock" size={14} />Make private</Button>
						<Button variant="outlined" onclick={() => setPrivateBulk(false)}><Icon name="unlock" size={14} />Make public</Button>
						<Button variant="ghost" onclick={() => (librarySelected = new Set())}>Clear</Button>
					</div>
				{/if}

				<!-- Documents (and, while browsing, subfolders) as cards/tiles —
				     sits directly below the breadcrumb/Kind facet rather than
				     behind a drill-down click. -->
				<div class="doc-grid" class:list-view={viewMode === 'list'}>
					{#if !searching}
						{#each visibleSubfolders as node (node.path)}
							<div
								class="folder-card"
								draggable="true"
								ondragstart={() => (draggedFolderPath = node.path)}
								ondragend={() => (draggedFolderPath = null)}
								ondragover={(e) => e.preventDefault()}
								ondrop={(e) => { e.preventDefault(); handleDropOnFolder(node.path); }}
							>
								<button class="folder-card-open" onclick={() => { currentPath = node.path; page = 1; }}>
									<Icon name="folder" size={28} />
									<span class="folder-card-name">{node.name}</span>
									<span class="count">{node.count}</span>
								</button>
								<span class="folder-card-actions">
									<button title="Rename folder" aria-label="Rename {node.name}" onclick={() => askRenameFolder(node.path)}>
										<Icon name="edit" size={12} />
									</button>
									<button title="Privatize folder" aria-label="Privatize {node.name}" onclick={() => setFolderPrivate(node.path, true)}>
										<Icon name="lock" size={12} />
									</button>
									<button title="Make folder public" aria-label="Make {node.name} public" onclick={() => setFolderPrivate(node.path, false)}>
										<Icon name="unlock" size={12} />
									</button>
									<button title="Delete folder" aria-label="Delete {node.name}" onclick={() => askDeleteFolder(node.path, node.count)}>
										<Icon name="trash" size={12} />
									</button>
								</span>
							</div>
						{/each}
					{/if}
					<!-- Staged items as cards, right in the grid — specs/v6.12:
					     no separate "staged for review" tab or manual Ingest
					     click any more. A staged item IS the in-queue state;
					     this card disappears on its own once the job finishes
					     and the real document takes its place in `pageItems`
					     (app/main.py's _run_staged_ingest_job deletes the
					     staged row on success). Root only — a staged item has
					     no folder_path yet — and not in table view (its own
					     column set doesn't fit a progress bar well; icons/list
					     cover the common case). -->
					{#if !searching && !currentPath && viewMode !== 'table'}
						{#each data.staged ?? [] as item (item.id)}
							<div class="doc-card doc-card-pending">
								<div class="doc-card-head">
									<span class="title-link pending-title">{item.filename ?? item.source_url ?? 'Pasted text'}</span>
									{#if item.kind === 'file'}
										<a class="icon-btn" href={stagedFileUrl(item)} target="_blank" rel="noopener" title="Preview the original file" aria-label="Preview {item.filename}"><Icon name="eye" /></a>
									{:else if item.kind === 'scraped_url'}
										<a class="icon-btn" href={item.source_url} target="_blank" rel="noopener" title="Open the source page" aria-label="Open source"><Icon name="external-link" /></a>
									{/if}
								</div>
								{#if jobsByStagedId[item.id]?.status === 'error'}
									<p class="hint job-error">{jobLabel(jobsByStagedId[item.id])}</p>
									<div class="doc-card-foot">
										<button class="view" onclick={() => ingestOne(item.id)} disabled={promotingId === item.id}>Retry</button>
										<button class="view danger" onclick={() => discardStaged(item.id)}>Discard</button>
									</div>
								{:else}
									<div class="job-progress">
										<div class="track"><div class="fill" style="width: {jobProgressPercent(jobsByStagedId[item.id] ?? { step: 'queued' })}%"></div></div>
										<span class="hint">{jobLabel(jobsByStagedId[item.id] ?? { status: 'queued', step: 'queued' })}</span>
									</div>
									<div class="doc-card-foot">
										<button
											class="view danger"
											onclick={() => discardStaged(item.id)}
											disabled={jobActive(jobsByStagedId[item.id])}
											title={jobActive(jobsByStagedId[item.id]) ? 'Already queued or running' : undefined}
										>Discard</button>
									</div>
								{/if}
							</div>
						{/each}
					{/if}
					{#if viewMode !== 'table'}
					{#each pageItems as s (s.id)}
						<div
							oncontextmenu={(e) => onDocContextMenu(e, s)}
							class="doc-card"
							draggable="true"
							ondragstart={() => (draggedId = s.id)}
							ondragend={() => (draggedId = null)}
						>
							<div class="doc-card-head">
								<input
									type="checkbox"
									checked={librarySelected.has(s.id)}
									onchange={() => toggleLibrarySelected(s.id)}
									aria-label="Select {s.title}"
								/>
								<a class="title-link" href="/admin/{s.id}" title={s.title}>{s.title}</a>
								<div class="doc-card-actions">
									{#if needsFinalization.has(s.id)}
										<button class="icon-btn finalize-bell" onclick={() => (placementPreview = s)} title="Review where this was filed" aria-label="Review placement for {s.title}"><Icon name="bell" /></button>
									{/if}
									<Menu label="More actions for {s.title}">
										{#snippet items()}
											<a href="/admin/{s.id}"><Icon name="eye" size={15} /> View</a>
											<button onclick={() => askMove(s)}><Icon name="folder" size={15} /> Move to folder…</button>
											<button onclick={() => setPrivate(s, !s.is_private)}>
												<Icon name={s.is_private ? 'lock' : 'unlock'} size={15} /> {s.is_private ? 'Make public' : 'Make private'}
											</button>
											{#if s.is_private}
												<button onclick={() => askAccess(s)}><Icon name="users" size={15} /> Edit access…</button>
											{/if}
											<button onclick={() => askAssignUploader(s)}><Icon name="user-card" size={15} /> {s.uploaded_by ? 'Reassign uploader…' : 'Assign uploader…'}</button>
											<button class="danger" onclick={() => askDelete(s)}><Icon name="trash" size={15} /> Remove from library</button>
										{/snippet}
									</Menu>
								</div>
							</div>
							<div class="tags">
								{#each s.topics ?? [] as tag (tag)}
									<button class="tag" onclick={() => removeTag(s, tag)} title="Remove tag">
										{tag} <span aria-hidden="true">&times;</span>
									</button>
								{/each}
								<input
									class="tag-input"
									type="text" placeholder="+ tag"
									value={newTagText[s.id] ?? ''}
									oninput={(e) => (newTagText = { ...newTagText, [s.id]: (e.target as HTMLInputElement).value })}
									onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(s); } }}
									onblur={() => addTag(s)}
								/>
							</div>
							<div class="doc-card-foot">
								<select
									class="doc-type-select"
									value={s.doc_type ?? ''}
									onchange={(e) => setDocType(s, (e.target as HTMLSelectElement).value)}
									aria-label="Content type for {s.title}"
								>
									<option value="">(type unset)</option>
									{#each DOC_TYPES as t (t)}<option value={t}>{t}</option>{/each}
								</select>
								{#if s.is_private}<Chip tone="warn">private</Chip>{/if}
								<label class="grade-label">
									Grade
									<input
										class="grade"
										type="number" min="1" max="10" value={s.grade}
										onchange={(e) => regrade(s, Number((e.target as HTMLInputElement).value))}
									/>
								</label>
								<label class="folder-label">
									<Icon name="folder" size={13} />
									<input
										class="folder-input"
										type="text" placeholder="(root)" value={s.folder_path ?? ''}
										onblur={(e) => setFolder(s, (e.target as HTMLInputElement).value)}
									/>
								</label>
								<span class="hint">{(s.created_at ?? '').slice(0, 10)}</span>
							</div>
							{#if s.author || s.uploaded_by}
								<div class="doc-card-meta">
									<!-- Separate lines with their own icon + color, not one
									     run-on sentence (found live: "hard to distinguish them,
									     color and fonts are the same") — author (the book's own
									     byline) and uploader (who put it in this library) are
									     different facts about a document, not two clauses of
									     the same one. -->
									{#if s.author}<p class="meta-line"><Icon name="book" size={11} /> {s.author}</p>{/if}
									{#if s.uploaded_by}<p class="meta-line meta-uploader"><Icon name="user-card" size={11} /> {s.uploaded_by}</p>{/if}
								</div>
							{/if}
						</div>
					{:else}
						<!-- searching always shows feedback here even when
						     visibleSubfolders.length > 0 — found in review:
						     subfolder tiles are already hidden while
						     searching (the {#if !searching} above), so a
						     search that matches zero documents used to leave
						     this whole area blank with no "nothing matches"
						     message, indistinguishable from a stuck page. -->
						{#if searching || !visibleSubfolders.length}
							<!-- grid-column: 1/-1 — a single grid item inside
							     .doc-grid's auto-fill columns would otherwise
							     only get one narrow (min 16rem) track's width,
							     which the old plain-text hint got away with but
							     this richer icon/headline/CTA treatment needs
							     to span the full row to not look cramped. -->
							<div class="grid-empty">
								{#if !data.sources.length}
									<EmptyState
										icon="book"
										title="Your library is empty"
										body='Upload a document, paste text, or scrape a URL to start teaching Clinic.'
									>
										{#snippet action()}
											<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>
										{/snippet}
									</EmptyState>
								{:else if searching}
									<EmptyState icon="search" title="Nothing matches that search" body="Try a different term, or clear the search.">
										{#snippet action()}
											<Button variant="ghost" onclick={() => { q = ''; page = 1; }}>Clear search</Button>
										{/snippet}
									</EmptyState>
								{:else}
									<EmptyState
										icon="folder"
										title="This folder is empty"
										body="Upload a document here, or browse to another folder."
									>
										{#snippet action()}
											<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>
										{/snippet}
									</EmptyState>
								{/if}
							</div>
						{/if}
					{/each}
					{/if}
				</div>

				{#if viewMode === 'table'}
					<!-- Explorer/Finder "Details"/"Columns" view — a compact
					     sortable-by-eye table instead of the card grid, same
					     underlying pageItems and same edit affordances (tags
					     stay comma-joined/read-only here; use Icons or List to
					     edit them inline). -->
					<div class="doc-table-wrap">
						<table class="doc-table">
							<thead>
								<tr>
									<th></th>
									<th>Title</th>
									<th>Type</th>
									<th>Author</th>
									<th>Uploaded by</th>
									<th>Folder</th>
									<th>Tags</th>
									<th>Grade</th>
									<th>Date</th>
									<th></th>
								</tr>
							</thead>
							<tbody>
								<!-- Staged/in-progress items, same root-only condition
								     as the Icons/List pending cards — found in review:
								     Table view had no visibility into the queue at all
								     (no row, no per-item Retry/Discard), only the
								     aggregate status bar above. -->
								{#if !searching && !currentPath}
									{#each data.staged ?? [] as item (item.id)}
										<tr class="staged-row">
											<td colspan="9">
												<span class="pending-title">{item.filename ?? item.source_url ?? 'Pasted text'}</span>
												{#if jobsByStagedId[item.id]?.status === 'error'}
													<span class="hint job-error">{jobLabel(jobsByStagedId[item.id])}</span>
												{:else}
													<span class="job-progress table-job-progress">
														<span class="track"><span class="fill" style="width: {jobProgressPercent(jobsByStagedId[item.id] ?? { step: 'queued' })}%"></span></span>
														<span class="hint">{jobLabel(jobsByStagedId[item.id] ?? { status: 'queued', step: 'queued' })}</span>
													</span>
												{/if}
											</td>
											<td class="doc-table-actions">
												{#if jobsByStagedId[item.id]?.status === 'error'}
													<button class="icon-btn" onclick={() => ingestOne(item.id)} disabled={promotingId === item.id} title="Retry" aria-label="Retry {item.filename}"><Icon name="refresh" size={15} /></button>
												{/if}
												<button
													class="icon-btn danger"
													onclick={() => discardStaged(item.id)}
													disabled={jobActive(jobsByStagedId[item.id])}
													title={jobActive(jobsByStagedId[item.id]) ? 'Already queued or running' : 'Discard'}
													aria-label="Discard {item.filename}"
												><Icon name="trash" size={15} /></button>
											</td>
										</tr>
									{/each}
								{/if}
								{#each pageItems as s (s.id)}
									<tr oncontextmenu={(e) => onDocContextMenu(e, s)}>
										<td>
											<input
												type="checkbox"
												checked={librarySelected.has(s.id)}
												onchange={() => toggleLibrarySelected(s.id)}
												aria-label="Select {s.title}"
											/>
										</td>
										<td>
											<a class="title-link" href="/admin/{s.id}" title={s.title}>{s.title}</a>
											{#if s.is_private}<span class="private-badge" title="Private" aria-label="Private"><Icon name="lock" size={12} /></span>{/if}
										</td>
										<td class="hint">{s.doc_type || '—'}</td>
										<td class="hint">{s.author || '—'}</td>
										<td class="hint">{s.uploaded_by || '—'}</td>
										<td class="hint">{s.folder_path || '(root)'}</td>
										<td class="hint">{(s.topics ?? []).join(', ') || '—'}</td>
										<td class="hint">{s.grade}</td>
										<td class="hint">{(s.created_at ?? '').slice(0, 10)}</td>
										<td class="doc-table-actions">
											{#if needsFinalization.has(s.id)}
												<button class="icon-btn finalize-bell" onclick={() => (placementPreview = s)} title="Review where this was filed" aria-label="Review placement for {s.title}"><Icon name="bell" size={15} /></button>
											{/if}
											<Menu label="More actions for {s.title}">
												{#snippet items()}
													<a href="/admin/{s.id}"><Icon name="eye" size={15} /> View</a>
													<button onclick={() => askMove(s)}><Icon name="folder" size={15} /> Move to folder…</button>
													<button onclick={() => setPrivate(s, !s.is_private)}>
														<Icon name={s.is_private ? 'lock' : 'unlock'} size={15} /> {s.is_private ? 'Make public' : 'Make private'}
													</button>
													{#if s.is_private}
														<button onclick={() => askAccess(s)}><Icon name="users" size={15} /> Edit access…</button>
													{/if}
													<button onclick={() => askAssignUploader(s)}><Icon name="user-card" size={15} /> {s.uploaded_by ? 'Reassign uploader…' : 'Assign uploader…'}</button>
													<button class="danger" onclick={() => askDelete(s)}><Icon name="trash" size={15} /> Remove from library</button>
												{/snippet}
											</Menu>
										</td>
									</tr>
								{:else}
									<tr><td colspan="10">
										{#if !data.sources.length}
											<EmptyState
												icon="book"
												title="Your library is empty"
												body='Upload a document, paste text, or scrape a URL to start teaching Clinic.'
											>
												{#snippet action()}
													<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>
												{/snippet}
											</EmptyState>
										{:else if searching}
											<EmptyState icon="search" title="Nothing matches that search" body="Try a different term, or clear the search.">
												{#snippet action()}
													<Button variant="ghost" onclick={() => { q = ''; page = 1; }}>Clear search</Button>
												{/snippet}
											</EmptyState>
										{:else}
											<EmptyState
												icon="folder"
												title="This folder is empty"
												body="Upload a document here, or browse to another folder."
											>
												{#snippet action()}
													<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>
												{/snippet}
											</EmptyState>
										{/if}
									</td></tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}

				{#if totalPages > 1}
					<div class="pager">
						<button class="view" onclick={() => (page = shownPage - 1)} disabled={shownPage <= 1}>← Prev</button>
						<span class="hint">Page {shownPage} of {totalPages} ({filtered.length} document{filtered.length === 1 ? '' : 's'})</span>
						<button class="view" onclick={() => (page = shownPage + 1)} disabled={shownPage >= totalPages}>Next →</button>
					</div>
				{/if}
			</div>
		</div>
	{:else if mainTab === 'tree'}
		<!-- Unified folders+documents tree, reusing already-loaded data.sources
		     / data.folders — no new fetch, so this tab paints in well under
		     100ms. Clicking a folder jumps into the Library tab at that path;
		     clicking a document (a real <a href>) opens its detail page. -->
		<div class="tree-view-pane">
			<div
				class="node root-node"
				ondragover={(e) => e.preventDefault()}
				ondrop={(e) => { e.preventDefault(); handleDropOnFolder(''); }}
			>
				<span class="name"><Icon name="folder" size={13} /> Library <span class="count">{data.sources.length}</span></span>
			</div>
			<FolderTree
				nodes={folderTree}
				activePath={currentPath}
				docs={rootDocs}
				showDocs
				onSelect={(path) => { currentPath = path; mainTab = 'library'; page = 1; }}
				onDrop={handleDropOnFolder}
				onRename={askRenameFolder}
				onPrivatize={setFolderPrivate}
				onDelete={(path, count) => askDeleteFolder(path, count)}
			/>
		</div>
	{:else if mainTab === 'graph'}
		{#if data.graph}
			<p class="hint graph-stats">{data.graph.entities ?? 0} concepts · {data.graph.mentions ?? 0} links · {(data.graph.unlinked ?? []).length} unlinked sources</p>
		{/if}
		{#if conceptGraphLoading}
			<p class="hint">Loading the concept graph…</p>
		{:else}
			<GraphView nodes={conceptGraph?.nodes ?? []} edges={conceptGraph?.edges ?? []} />
		{/if}
	{/if}
	</div>
</Spotlight>

{#snippet libraryActions()}
	<Button variant="outlined" onclick={() => { maintenanceKind = 'relink'; maintenanceOpen = true; }}>Relink</Button>
	<Button variant="outlined" onclick={() => { maintenanceKind = 'consolidate'; maintenanceOpen = true; }}>Consolidate</Button>
	<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>
{/snippet}

<Dialog bind:open={maintenanceOpen} title={maintenanceKind === 'relink' ? 'Relink unlinked sources' : 'Consolidate entities'}>
	<p>
		{maintenanceKind === 'relink'
			? 'Build the knowledge graph for any ingested sources that have none yet. This can take a while for a large backlog.'
			: 'Let the model suggest entity merges, then rewrite the graph to match. Requires Neo4j APOC.'}
	</p>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (maintenanceOpen = false)}>Cancel</Button>
		<Button onclick={runMaintenance} loading={maintenanceRunning}>Run</Button>
	{/snippet}
</Dialog>

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
				<Button onclick={stageFile} loading={staging} disabled={!selectedFile}>Upload and queue for ingestion</Button>
			</div>
		{:else if ingestTab === 'text'}
			<form onsubmit={stageText} class="ingest">
				<TextField label="Paste text" type="textarea" bind:value={text} placeholder="Paste an article, note, or transcript…" />
				<Button type="submit" loading={staging}>Add and queue for ingestion</Button>
			</form>
		{:else if ingestTab === 'url'}
			<form onsubmit={scrapeUrl} class="ingest">
				<TextField label="Page URL" bind:value={url} placeholder="https://…" required />
				<p class="hint">Fetches the page and extracts its content only — no navigation, headers, footers, or ads — via a bounded AI pass. Nothing is summarized or rephrased.</p>
				{#if scraping}
					<div class="scrape-progress" aria-hidden="true"><div class="bar"></div></div>
					<p class="hint">Fetching and extracting…</p>
				{/if}
				<Button type="submit" loading={scraping}>Scrape and queue for ingestion</Button>
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

<Dialog bind:open={renamingFolder} title="Rename folder">
	<form onsubmit={renameFolder} id="rf-form">
		<TextField label="Current path" bind:value={renameOldPath} disabled />
		<TextField label="New path" bind:value={renameNewPath} placeholder="e.g. Hormones/Menopause" />
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (renamingFolder = false)}>Cancel</Button>
		<Button onclick={renameFolder} loading={renamingSubmitting}>Rename</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={newFolderOpen} title="New folder">
	<form onsubmit={createFolder} id="nf-form">
		<p class="hint">Inside "{currentPath || 'Library'}".</p>
		<TextField label="Folder name" bind:value={newFolderName} placeholder="e.g. Menopause" />
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (newFolderOpen = false)}>Cancel</Button>
		<Button onclick={createFolder} loading={newFolderSubmitting}>Create</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={deletingFolderOpen} title="Delete folder">
	{#if deletingFolder}
		<p>
			Delete "{deletingFolder.path}"
			{#if deletingFolder.count}and every document in it, including subfolders
				({deletingFolder.count} document{deletingFolder.count === 1 ? '' : 's'} total){/if}?
			This can't be undone.
		</p>
	{/if}
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (deletingFolderOpen = false)}>Cancel</Button>
		<Button variant="danger" onclick={confirmDeleteFolder} loading={deletingFolderSubmitting}>Delete</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={movingOpen} title="Move to folder">
	{#if movingSource}
		<form onsubmit={confirmMove} id="mv-form">
			<p class="hint">Moving "{movingSource.title.slice(0, 60)}".</p>
			<TextField label="Folder path" bind:value={movingPath} placeholder="(root)" />
			{#if folderPaths.length}
				<p class="hint">Existing folders:</p>
				<div class="move-suggestions">
					{#each folderPaths as p (p)}
						<button type="button" class="fchip" onclick={() => (movingPath = p)}>{p}</button>
					{/each}
				</div>
			{/if}
		</form>
	{/if}
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (movingOpen = false)}>Cancel</Button>
		<Button onclick={confirmMove}>Move</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={uploadedByOpen} title="Assign uploader">
	{#if uploadedByEditing}
		<form onsubmit={confirmAssignUploader} id="ub-form">
			<p class="hint">
				Who uploaded "{uploadedByEditing.title.slice(0, 60)}"? Nothing is recoverable automatically for
				this document — uploader is only captured going forward (specs/v6.11).
			</p>
			<TextField label="Uploaded by" bind:value={uploadedByValue} placeholder="name or email" />
		</form>
	{/if}
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (uploadedByOpen = false)}>Cancel</Button>
		<Button onclick={confirmAssignUploader}>Save</Button>
	{/snippet}
</Dialog>

<!-- Shown once per completed ingest (watchJob's 'done' branch) — the
     Reader's suggested folder/tags are already applied by the time this
     opens, so this is "here's where it landed, adjust if you want" rather
     than a pre-commit approval gate. Reuses the same setFolder/addTag/
     removeTag writes the library's own doc-cards already use. -->
<Dialog bind:open={() => !!placementPreview, (v) => { if (!v) { if (placementPreview) dismissFinalization(placementPreview.id); placementPreview = null; } }} title="Placed in library">
	{#if placementPreview}
		<p class="hint">"{placementPreview.title.slice(0, 80)}" was ingested and filed as shown below — the Reader suggested these, adjust them if needed.</p>
		<select
			class="doc-type-select"
			value={placementPreview.doc_type ?? ''}
			onchange={(e) => setDocType(placementPreview, (e.target as HTMLSelectElement).value)}
			aria-label="Content type"
		>
			<option value="">(type unset)</option>
			{#each DOC_TYPES as t (t)}<option value={t}>{t}</option>{/each}
		</select>
		<label class="folder-label">
			<Icon name="folder" size={13} />
			<input
				class="folder-input"
				type="text" placeholder="(root)" value={placementPreview.folder_path ?? ''}
				onblur={(e) => setFolder(placementPreview, (e.target as HTMLInputElement).value)}
			/>
		</label>
		{#if folderPaths.length}
			<div class="move-suggestions">
				{#each folderPaths as p (p)}
					<button type="button" class="fchip" onclick={() => setFolder(placementPreview, p)}>{p}</button>
				{/each}
			</div>
		{/if}
		<div class="tags placement-tags">
			{#each placementPreview.topics ?? [] as tag (tag)}
				<button class="tag" onclick={() => removeTag(placementPreview, tag)} title="Remove tag">
					{tag} <span aria-hidden="true">&times;</span>
				</button>
			{/each}
			<input
				class="tag-input"
				type="text" placeholder="+ tag"
				value={newTagText[placementPreview.id] ?? ''}
				oninput={(e) => (newTagText = { ...newTagText, [placementPreview.id]: (e.target as HTMLInputElement).value })}
				onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(placementPreview); } }}
				onblur={() => addTag(placementPreview)}
			/>
		</div>
	{/if}
	{#snippet footer()}
		<Button onclick={() => { if (placementPreview) dismissFinalization(placementPreview.id); placementPreview = null; }}>Got it</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={accessOpen} title="Edit access">
	{#if accessEditing}
		<p class="hint">Who can still see "{accessEditing.title.slice(0, 60)}" despite it being private.</p>
	{/if}
	<ul class="access-list">
		{#each data.practitioners as p (p.id)}
			<li>
				<label>
					<input
						type="checkbox"
						checked={accessSelected.has(p.id)}
						onchange={() => toggleAccessSelected(p.id)}
					/>
					{p.name} <span class="hint">{p.email}</span>
				</label>
			</li>
		{:else}
			<li class="hint">No practitioners yet.</li>
		{/each}
	</ul>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (accessOpen = false)}>Cancel</Button>
		<Button onclick={saveAccess} loading={accessSubmitting}>Save</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={duplicateOpen} title="Already in the library">
	<p>{duplicateMessage}</p>
	{#snippet footer()}
		<button class="view" onclick={() => (duplicateOpen = false)}>Cancel</button>
		<button class="view danger" onclick={discardDuplicate}>Discard staged item</button>
		<button class="view" onclick={replaceDuplicate}>Replace old version</button>
	{/snippet}
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
	.search-bar { margin-bottom: var(--space-4); display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
	.search-input-wrap { position: relative; flex: 1 1 16rem; min-width: 0; }
	.graph-stats { margin: 0 0 var(--space-4); }
	.search {
		width: 100%; font-size: var(--text-lg); padding: var(--space-4) var(--space-5) var(--space-4) var(--space-4);
		border: 1px solid var(--line-2); border-radius: var(--r-lg); background: var(--panel);
		color: var(--ink);
		transition: border-color .15s var(--ease), box-shadow .15s var(--ease);
	}
	.sort-control {
		display: flex; align-items: center; gap: .2rem; flex: 0 0 auto;
		border: 1px solid var(--line-2); border-radius: var(--r-lg); padding: .2rem .2rem .2rem .5rem;
	}
	.sort-control select {
		border: none; background: none; font: inherit; font-size: var(--text-sm); color: var(--ink); cursor: pointer;
	}
	.sort-dir {
		display: inline-flex; align-items: center; justify-content: center;
		width: 1.6rem; height: 1.6rem; border: none; background: none; cursor: pointer;
		color: var(--muted); border-radius: var(--r);
		transition: transform var(--duration-fast, .12s) var(--ease);
	}
	.sort-dir:hover { background: var(--panel-2); color: var(--accent); }
	/* The chevron icon points down natively — that's already correct for
	   descending; rotated 180deg (pointing up) for ascending. */
	.sort-dir:not(.desc) { transform: rotate(180deg); }
	.sort-dir:not(.desc):hover { transform: rotate(180deg); }
	.view-toggle { display: flex; gap: .1rem; border: 1px solid var(--line-2); border-radius: var(--r-lg); padding: .2rem; flex: 0 0 auto; }
	.view-toggle button {
		border: none; background: none; cursor: pointer; color: var(--muted); padding: .5rem .6rem;
		border-radius: var(--r); display: inline-flex;
	}
	.view-toggle button.active { color: var(--accent); background: var(--accent-soft); }
	.view-toggle button:hover:not(.active) { background: var(--panel-2); }
	.search:focus {
		outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);
	}
	.search-clear {
		position: absolute; right: var(--space-3); top: 50%; transform: translateY(-50%);
		border: none; background: none; cursor: pointer; font-size: 1.3rem; line-height: 1;
		color: var(--muted); padding: .2rem .4rem;
	}
	.search-clear:hover { color: var(--ink); }
	/* One short row, scrolling on the x axis rather than wrapping — a tile
	   stays a compact name+count pill no matter how many categories exist. */
	.directory-row {
		display: flex; gap: var(--space-2); overflow-x: auto; overflow-y: hidden;
		padding-bottom: var(--space-2); margin-bottom: var(--space-4);
	}
	.dir-tile {
		flex: 0 0 auto; display: inline-flex; align-items: center; gap: .4rem; white-space: nowrap;
		text-align: left; cursor: pointer; font: inherit; font-size: var(--text-sm);
		border: 1px solid var(--line); background: var(--panel-2); color: var(--ink);
		border-radius: 99px; padding: .45rem .85rem;
		transition: border-color .15s var(--ease), background .15s var(--ease), color .15s var(--ease);
	}
	.dir-tile:hover { border-color: var(--accent); background: var(--accent-soft); }
	.dir-tile.active { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-ink); }
	.dir-name { font-weight: 650; }
	.dir-count {
		font-size: var(--text-xs); color: var(--muted); background: var(--panel);
		border-radius: 99px; padding: .1rem .45rem;
	}
	.dir-tile.active .dir-count { color: inherit; background: rgba(255, 255, 255, .35); }
	.doc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr)); gap: var(--space-3); }
	.grid-empty { grid-column: 1 / -1; }
	.doc-grid.list-view { grid-template-columns: 1fr; }
	.doc-table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: var(--r-lg); }
	.doc-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
	.doc-table th, .doc-table td {
		padding: .5rem .6rem; text-align: left; border-bottom: 1px solid var(--line);
		white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 16rem;
	}
	.doc-table th { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }
	.doc-table tbody tr:hover { background: var(--panel-2); }
	.doc-table-actions { display: flex; align-items: center; gap: .2rem; white-space: nowrap; }
	.private-badge { display: inline-flex; color: var(--muted); margin-left: .3rem; vertical-align: middle; }
	.library-layout { display: flex; gap: var(--space-5); align-items: flex-start; }
	.folder-sidebar {
		flex: 0 0 14rem; min-width: 0; border-right: 1px solid var(--line); padding-right: var(--space-4);
		max-height: 70vh; overflow-y: auto; position: sticky; top: var(--space-4);
	}
	.library-main { flex: 1 1 auto; min-width: 0; }
	.breadcrumb-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; }
	.breadcrumb { display: flex; align-items: center; gap: .3rem; margin-bottom: var(--space-3); font-size: var(--text-sm); flex-wrap: wrap; }
	.move-suggestions { display: flex; flex-wrap: wrap; gap: .3rem; margin-top: .3rem; }
	.breadcrumb button {
		border: none; background: none; cursor: pointer; font: inherit; color: var(--accent); padding: .1rem .2rem;
	}
	.breadcrumb button:disabled { color: var(--ink); cursor: default; font-weight: 650; }
	.breadcrumb .sep { color: var(--muted); }
	.folder-card {
		position: relative; border: 1px solid var(--line); border-radius: var(--r); background: var(--panel);
		min-height: 7rem;
	}
	.folder-card:hover { border-color: var(--accent); background: var(--accent-soft); }
	.folder-card-open {
		display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .2rem;
		width: 100%; height: 100%; min-height: 7rem; border: none; background: none; cursor: pointer;
		font: inherit; color: var(--ink); padding: var(--space-3) var(--space-2);
	}
	.folder-card-name { font-size: var(--text-sm); font-weight: 600; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
	.folder-card .count { color: var(--muted); font-size: var(--text-xs); }
	/* Always visible, not hover-revealed (matches doc-card-actions, and
	   hover never fires on touch) — absolutely positioned so this doesn't
	   affect the tile's own size either way, but consistency matters more
	   than the extra chrome being decorative most of the time. */
	.folder-card-actions { display: flex; gap: .2rem; position: absolute; top: .3rem; right: .3rem; }
	.folder-card-actions button {
		display: inline-flex; border: none; background: none; padding: .2rem; border-radius: var(--r); color: var(--muted); cursor: pointer;
	}
	.folder-card-actions button:hover { color: var(--accent); background: var(--panel); }
	/* Mirrors FolderTree.svelte's .node/.name/.count exactly — these two
	   rows (All sources / unfiled) sit above the real tree, not inside
	   it, since neither is a real folder_path value. */
	.folder-sidebar .root-node {
		display: flex; align-items: center; border-radius: var(--r); margin-bottom: .15rem;
	}
	.folder-sidebar .root-node:hover { background: var(--panel-2); }
	.folder-sidebar .root-node.active { background: var(--accent-soft); }
	.folder-sidebar .name {
		flex: 1 1 auto; display: flex; align-items: center; gap: .35rem; border: none; background: none;
		cursor: pointer; font: inherit; font-size: var(--text-sm); color: var(--ink); padding: .3rem 0; text-align: left;
	}
	.folder-sidebar .count { color: var(--muted); font-size: var(--text-xs); margin-left: auto; }
	.tree-view-pane { max-width: 36rem; }
	.tree-view-pane .root-node {
		display: flex; align-items: center; border-radius: var(--r); margin-bottom: .15rem;
	}
	.tree-view-pane .name {
		flex: 1 1 auto; display: flex; align-items: center; gap: .35rem; font-size: var(--text-sm);
		color: var(--ink); padding: .3rem 0;
	}
	.tree-view-pane .count { color: var(--muted); font-size: var(--text-xs); margin-left: auto; }
	@media (max-width: 900px) {
		.library-layout { flex-direction: column; }
		.folder-sidebar { flex: 0 0 auto; width: 100%; max-height: none; border-right: none; border-bottom: 1px solid var(--line); padding-right: 0; padding-bottom: var(--space-3); position: static; }
	}
	.bulk-bar { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); }
	.access-list { max-height: 50vh; overflow-y: auto; display: grid; gap: .4rem; list-style: none; padding: 0; }
	.access-list label { display: flex; align-items: center; gap: .5rem; }
	.doc-card {
		display: flex; flex-direction: column; gap: .4rem; padding: var(--space-3);
		border: 1px solid var(--line); border-radius: var(--r-lg); background: var(--panel-2);
	}
	.doc-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-2); }
	.doc-card-head input[type="checkbox"] { flex: 0 0 auto; margin-top: .25rem; }
	/* Clamped to 2 lines, not left to wrap freely — an unbounded title
	   (found live, 2026-11-03: "icon drift") squeezes into the narrow
	   column next to doc-card-actions' fixed width and wraps into many
	   short lines, leaving the action icons pinned to the top of a much
	   taller card instead of sitting beside the title the way every other
	   card does. */
	.doc-card-head .title-link {
		font-weight: 650; flex: 1 1 auto; min-width: 0;
		display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical;
		overflow: hidden;
	}
	.doc-card-actions { display: flex; gap: .3rem; flex: 0 0 auto; }
	.doc-card-foot { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); margin-top: auto; padding-top: .3rem; }
	.grade-label { display: flex; align-items: center; gap: .3rem; font-size: var(--text-xs); color: var(--muted); }
	.folder-label { display: flex; align-items: center; gap: .25rem; font-size: var(--text-xs); color: var(--muted); }
	.folder-input {
		width: 7.5rem; border: 1px solid var(--line-2); border-radius: var(--r);
		padding: .2rem .35rem; font: inherit; font-size: var(--text-xs); color: var(--ink); background: var(--panel);
	}
	.doc-type-select {
		border: 1px solid var(--line-2); border-radius: var(--r); padding: .15rem .35rem;
		font: inherit; font-size: var(--text-xs); color: var(--ink); background: var(--panel); cursor: pointer;
	}
	.doc-card-meta { margin: -.1rem 0 0; display: grid; gap: .15rem; }
	.meta-line { display: flex; align-items: center; gap: .3rem; margin: 0; font-size: var(--text-xs); color: var(--muted); }
	.meta-uploader { color: var(--accent); }
	.pager { display: flex; align-items: center; justify-content: center; gap: var(--space-4); margin-top: var(--space-5); }
	.fchip {
		font: inherit; font-size: var(--text-sm); cursor: pointer;
		border: 1px solid var(--line); background: var(--panel-2); color: var(--ink);
		border-radius: 99px; padding: .3rem .7rem; display: inline-flex; align-items: center; gap: .35rem;
		transition: background .15s var(--ease), border-color .15s var(--ease), color .15s var(--ease);
	}
	.fchip:hover { border-color: var(--accent); }
	.tags { display: flex; flex-wrap: wrap; align-items: center; gap: .25rem; margin-top: .25rem; }
	.tag {
		font: inherit; font-size: var(--text-xs); cursor: pointer; display: inline-flex; align-items: center; gap: .2rem;
		border: 1px solid var(--line); background: var(--panel-2); color: var(--muted);
		border-radius: 99px; padding: .08rem .45rem; line-height: 1.5;
	}
	.tag:hover { border-color: var(--danger); color: var(--danger); }
	.tag-input {
		font: inherit; font-size: var(--text-xs); border: 1px dashed var(--line-2); border-radius: 99px;
		padding: .08rem .45rem; background: transparent; color: var(--ink); width: 5rem;
	}
	.view {
		font: inherit; font-size: var(--text-sm); font-weight: 650; cursor: pointer;
		border: 1px solid var(--line); background: var(--panel); color: var(--accent-ink);
		border-radius: var(--r); padding: .3rem .7rem;
	}
	.view:hover { border-color: var(--accent); background: var(--accent-soft); }
	.view.danger { color: var(--danger); }
	.view.danger:hover { border-color: var(--danger); background: var(--danger-soft); }
	.icon-btn {
		display: inline-flex; align-items: center; justify-content: center; cursor: pointer;
		border: 1px solid var(--line); background: var(--panel); color: var(--accent-ink);
		border-radius: var(--r); width: 2rem; height: 2rem; padding: 0;
		transition: background .15s var(--ease), border-color .15s var(--ease);
	}
	.icon-btn:hover { border-color: var(--accent); background: var(--accent-soft); }
	.icon-btn.danger { color: var(--danger); }
	.icon-btn.danger:hover { border-color: var(--danger); background: var(--danger-soft); }
	.title-link {
		font: inherit; text-align: left; cursor: pointer; border: none; background: none;
		padding: 0; color: var(--ink); text-decoration: underline; text-decoration-color: transparent;
		transition: text-decoration-color .15s var(--ease);
	}
	.title-link:hover, .title-link:focus-visible { text-decoration-color: currentColor; }
	input.grade {
		width: 3.5rem; border: 1px solid var(--line-2); border-radius: var(--r);
		padding: .3rem .4rem; font: inherit; color: var(--ink); background: var(--panel);
	}
	.view:disabled { opacity: .5; cursor: not-allowed; }
	.queue-status-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-3); }
	.queue-status { margin: 0; }
	.doc-card-pending { opacity: .85; border-style: dashed; }
	.pending-title { font-weight: 650; overflow-wrap: anywhere; }
	.finalize-bell { color: var(--accent); }
	.finalize-bell:hover { color: var(--accent); }
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
	.staged-row td { background: var(--panel-2); }
	.staged-row .pending-title { margin-right: .6rem; }
	.table-job-progress { display: inline-flex; align-items: center; gap: .5rem; margin-top: 0; }
	.table-job-progress .track { width: 6rem; height: 5px; border-radius: 99px; background: var(--panel); overflow: hidden; }
	.table-job-progress .fill { height: 100%; border-radius: 99px; background: var(--accent); transition: width .3s var(--ease); }
</style>
