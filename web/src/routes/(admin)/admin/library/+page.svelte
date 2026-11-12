<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page as appPage } from '$app/state';
	import { invalidateAll } from '$app/navigation';
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { get, post, patch, put, del, ApiError } from '$lib/api';
	import { chunkedUpload } from '$lib/chunkedUpload';
	import { toast } from '$lib/stores/toast';
	import TextField from '$lib/components/TextField.svelte';
	import Tabs from '$lib/components/Tabs.svelte';
	import Button from '$lib/components/Button.svelte';
	import Dialog from '$lib/components/Dialog.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import FolderTree, { type TreeNode } from '$lib/components/FolderTree.svelte';
	import GraphView, { type GraphNode, type GraphEdge } from '$lib/components/GraphView.svelte';
	import Menu from '$lib/components/Menu.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import ContextMenu from '$lib/components/ContextMenu.svelte';

	let { data } = $props();

	// Graph maintenance: POST /api/relink and /api/consolidate with live SSE progress tracking.
	// Both the top progress banner and the confirm dialog show real-time percentage and detail.
	interface MaintenanceProgress {
		active: boolean;
		kind: 'relink' | 'consolidate';
		status: 'running' | 'done' | 'error' | 'cancelled';
		percentage: number;
		current: number;
		total: number;
		step: string;
		detail: string;
		result?: any;
		error?: string;
	}

	let maintenanceKind = $state<'relink' | 'consolidate' | null>(null);
	let maintenanceOpen = $state(false);
	let maintenanceRunning = $state(false);
	let maintenanceStopping = $state(false);
	let maintenanceProgress = $state<MaintenanceProgress | null>(null);
	let maintenanceDismissTimer: any = null;
	let maintenancePollTimer: any = null;

	async function pollMaintenanceStatus() {
		if (maintenancePollTimer) clearTimeout(maintenancePollTimer);
		try {
			const st = await get(fetch, '/maintenance/status');
			if (st && st.active) {
				maintenanceRunning = true;
				maintenanceKind = st.kind;
				maintenanceProgress = {
					active: true,
					kind: st.kind,
					status: 'running',
					percentage: Math.max(0, Math.min(100, Math.round(st.percentage ?? 0))),
					current: st.current ?? 0,
					total: st.total ?? 1,
					step: st.step || 'running',
					detail: st.detail || ''
				};
				maintenancePollTimer = setTimeout(pollMaintenanceStatus, 1500);
			} else if (st && st.status === 'done') {
				maintenanceRunning = false;
				maintenanceProgress = {
					active: false,
					kind: st.kind,
					status: 'done',
					percentage: 100,
					current: st.total ?? 1,
					total: st.total ?? 1,
					step: 'done',
					detail: st.detail || 'Finished.'
				};
				await invalidateAll();
				if (maintenanceDismissTimer) clearTimeout(maintenanceDismissTimer);
				maintenanceDismissTimer = setTimeout(() => {
					if (maintenanceProgress && maintenanceProgress.status === 'done') {
						maintenanceProgress = null;
					}
				}, 5000);
			} else {
				maintenanceRunning = false;
				if (maintenanceProgress?.status === 'running') {
					maintenanceProgress = null;
				}
			}
		} catch {
			maintenanceRunning = false;
		}
	}

	onMount(async () => {
		try {
			const st = await get(fetch, '/maintenance/status');
			if (st && st.active) {
				maintenanceRunning = true;
				maintenanceKind = st.kind;
				maintenanceProgress = {
					active: true,
					kind: st.kind,
					status: 'running',
					percentage: Math.max(0, Math.min(100, Math.round(st.percentage ?? 0))),
					current: st.current ?? 0,
					total: st.total ?? 1,
					step: st.step || 'running',
					detail: st.detail || ''
				};
				pollMaintenanceStatus();
			}
		} catch {}
	});

	onDestroy(() => {
		if (maintenancePollTimer) clearTimeout(maintenancePollTimer);
		if (maintenanceDismissTimer) clearTimeout(maintenanceDismissTimer);
	});

	async function stopMaintenanceTask() {
		maintenanceStopping = true;
		try {
			await post(fetch, '/maintenance/stop', {});
			toast('Stopping maintenance task…');
			if (maintenanceProgress) {
				maintenanceProgress.status = 'cancelled';
				maintenanceProgress.active = false;
				maintenanceProgress.detail = 'Stopped by user.';
			}
			maintenanceRunning = false;
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			maintenanceStopping = false;
		}
	}

	async function runMaintenance() {
		if (!maintenanceKind) return;
		const kind = maintenanceKind;
		maintenanceRunning = true;
		maintenanceProgress = {
			active: true,
			kind,
			status: 'running',
			percentage: 0,
			current: 0,
			total: 1,
			step: 'start',
			detail: kind === 'relink' ? 'Searching for unlinked documents…' : 'Preparing entity consolidation…'
		};

		try {
			const res = await fetch(`${PUBLIC_API_BASE}/api/${kind}?stream=true`, {
				method: 'POST',
				credentials: 'include',
				headers: { Accept: 'text/event-stream' }
			});

			if (!res.ok || !res.body) {
				const body = await res.json().catch(() => ({}));
				throw new Error(body?.detail?.message || body?.detail || res.statusText);
			}

			const reader = res.body.getReader();
			const decoder = new TextDecoder();
			let buf = '';

			for (;;) {
				const { value, done } = await reader.read();
				if (done) break;
				buf += decoder.decode(value, { stream: true });
				let idx: number;
				while ((idx = buf.indexOf('\n\n')) !== -1) {
					const frame = buf.slice(0, idx);
					buf = buf.slice(idx + 2);
					const line = frame.split('\n').find((l) => l.startsWith('data: '));
					if (!line) continue;
					try {
						const ev = JSON.parse(line.slice(6));
						if (ev.event === 'error') {
							throw new Error(ev.message || 'Maintenance failed.');
						}
						const pct = Math.max(0, Math.min(100, Math.round(ev.percentage ?? 0)));
						maintenanceProgress = {
							active: ev.event !== 'done',
							kind,
							status: ev.event === 'done' ? 'done' : 'running',
							percentage: pct,
							current: ev.current ?? 0,
							total: ev.total ?? 1,
							step: ev.step || (ev.event === 'done' ? 'done' : 'running'),
							detail: ev.detail || '',
							result: ev.result
						};

						if (ev.event === 'done') {
							maintenanceRunning = false;
							const finalRes = ev.result || {};
							toast(
								kind === 'relink'
									? `Linked ${finalRes.linked?.length ?? 0} source(s), ${finalRes.failed?.length ?? 0} failed.`
									: `Merged ${finalRes.entity?.absorbed ?? 0} entit${finalRes.entity?.absorbed === 1 ? 'y' : 'ies'}.`
							);
							await invalidateAll();
							if (maintenanceDismissTimer) clearTimeout(maintenanceDismissTimer);
							maintenanceDismissTimer = setTimeout(() => {
								if (maintenanceProgress && maintenanceProgress.status === 'done') {
									maintenanceProgress = null;
								}
							}, 5000);
						}
					} catch (e: any) {
						if (e.message && e.message !== 'Unexpected end of JSON input') {
							throw e;
						}
					}
				}
			}
		} catch (err: any) {
			toast(err.message, 'alert');
			if (maintenanceProgress) {
				maintenanceProgress = {
					...maintenanceProgress,
					active: false,
					status: 'error',
					detail: err.message || 'Error running maintenance.'
				};
			}
		} finally {
			maintenanceRunning = false;
		}
	}

	let ingestOpen = $state(false);
	let ingestTab = $state('upload');
	let mainTab = $state<'library' | 'tags' | 'graph'>((appPage.url.searchParams.get('mode') as any) || (appPage.url.searchParams.get('tab') as any) || 'library');
	let currentTag = $state(appPage.url.searchParams.get('tag') ?? '');
	let selectedTagPath = $state<string | null>(null);
	let draggedTagPath = $state<string | null>(null);
	let customTags = $state<string[]>([]);
	let newCategoryOpen = $state(false);
	let newCategoryName = $state('');
	let renameTagOpen = $state(false);
	let renameTagOld = $state('');
	let renameTagNew = $state('');
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
	const pendingTargetFolders: Record<string, string> = {};
	const pendingTargetTags: Record<string, string> = {};

	// The just-ingested document, shown in the "Placed in library" dialog
	// right after a job finishes — the Reader already chose a folder and
	// tags at ingest time (app/ingestion/pipeline.py's suggested_folder /
	// topics), but nothing surfaced that choice to the admin before this;
	// the toast alone named the action, not the result.
	// specs/v15/05 — Multi-file placement confirmation upon finishing ingestion
	interface PendingPlacement {
		documentId: string;
		source: any;
		title: string;
		filename: string;
		currentFolder: string;
		suggestedFolder: string;
		selectedFolder: string;
		isCreatingNewFolder: boolean;
		newFolderName: string;
		docType?: string;
		suggestedTags: string[];
		selectedTags: string[];
		newTagInput: string;
	}

	let pendingPlacements = $state<PendingPlacement[]>([]);
	let placementDialogOpen = $state(false);

	let placementPreview = $state<any | null>(null);
	let needsFinalization = $state<Set<string>>(new Set());
	function dismissFinalization(id: string) {
		needsFinalization = new Set([...needsFinalization].filter((x) => x !== id));
		pendingPlacements = pendingPlacements.filter((p) => p.documentId !== id);
		if (pendingPlacements.length === 0) {
			placementDialogOpen = false;
		}
	}

	function addTagToPlacement(item: PendingPlacement, rawTag: string) {
		const cleaned = rawTag.trim().toLowerCase();
		if (!cleaned) return;
		if (!item.selectedTags.includes(cleaned)) {
			item.selectedTags = [...item.selectedTags, cleaned];
		}
		item.newTagInput = '';
	}

	function removeTagFromPlacement(item: PendingPlacement, tagToRemove: string) {
		item.selectedTags = item.selectedTags.filter((t) => t !== tagToRemove);
	}

	function toggleAiTagSuggestion(item: PendingPlacement, tag: string) {
		if (item.selectedTags.includes(tag)) {
			item.selectedTags = item.selectedTags.filter((t) => t !== tag);
		} else {
			item.selectedTags = [...item.selectedTags, tag];
		}
	}

	function openPlacementForDoc(s: any) {
		const existing = pendingPlacements.find((p) => p.documentId === s.id);
		if (!existing) {
			const suggested = s.suggested_folder || s.folder_path || '';
			const aiTopics = (s.topics ?? []).map((t: string) => t.trim().toLowerCase()).filter(Boolean);
			pendingPlacements = [
				...pendingPlacements,
				{
					documentId: s.id,
					source: s,
					title: s.title,
					filename: s.original_filename || s.title,
					currentFolder: s.folder_path || '',
					suggestedFolder: suggested,
					selectedFolder: suggested,
					isCreatingNewFolder: false,
					newFolderName: '',
					docType: s.doc_type || '',
					suggestedTags: aiTopics,
					selectedTags: [...aiTopics],
					newTagInput: ''
				}
			];
		}
		placementDialogOpen = true;
	}

	async function confirmSinglePlacement(item: PendingPlacement) {
		const targetFolder = item.isCreatingNewFolder ? item.newFolderName.trim() : item.selectedFolder;
		const targetTags = item.selectedTags.map((t) => t.trim().toLowerCase()).filter(Boolean);
		pendingPlacements = pendingPlacements.filter((p) => p.documentId !== item.documentId);
		needsFinalization = new Set([...needsFinalization].filter((id) => id !== item.documentId));
		if (pendingPlacements.length === 0) {
			placementDialogOpen = false;
		}
		try {
			await setFolder(item.source, targetFolder);
			await setTopics(item.source, targetTags);
			toast(`Confirmed "${item.title.slice(0, 30)}" → ${targetFolder || '(root)'} with ${targetTags.length} tag${targetTags.length === 1 ? '' : 's'}.`);
		} catch (err: any) {
			toast(`Failed to update "${item.title}": ${err.message}`, 'alert');
		}
	}

	async function confirmAllPlacements() {
		if (!pendingPlacements.length) return;
		const toProcess = [...pendingPlacements];
		pendingPlacements = [];
		placementDialogOpen = false;
		let successCount = 0;
		for (const item of toProcess) {
			needsFinalization = new Set([...needsFinalization].filter((id) => id !== item.documentId));
			const targetFolder = item.isCreatingNewFolder ? item.newFolderName.trim() : item.selectedFolder;
			const targetTags = item.selectedTags.map((t) => t.trim().toLowerCase()).filter(Boolean);
			try {
				await setFolder(item.source, targetFolder);
				await setTopics(item.source, targetTags);
				successCount++;
			} catch (err: any) {
				toast(`Failed to update "${item.title}": ${err.message}`, 'alert');
			}
		}
		if (successCount > 0) {
			toast(`Confirmed destination & tags for ${successCount} file${successCount === 1 ? '' : 's'}.`);
		}
	}

	$effect(() => {
		const existingSourceIds = new Set((data.sources ?? []).map((x: any) => x.id));
		if (placementPreview && !existingSourceIds.has(placementPreview.id)) {
			placementPreview = null;
		}
		if (pendingPlacements.length) {
			const valid = pendingPlacements.filter((p) => existingSourceIds.has(p.documentId));
			if (valid.length !== pendingPlacements.length) {
				pendingPlacements = valid;
				if (pendingPlacements.length === 0) {
					placementDialogOpen = false;
				}
			}
			for (const p of pendingPlacements) {
				const fresh = (data.sources ?? []).find((x: any) => x.id === p.documentId);
				if (fresh) p.source = fresh;
			}
		}
		if (needsFinalization.size) {
			const valid = new Set([...needsFinalization].filter((id) => existingSourceIds.has(id)));
			if (valid.size !== needsFinalization.size) {
				needsFinalization = valid;
			}
		}
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
					let placed = (data.sources ?? []).find((x: any) => x.id === job.result_document_id);
					if (!placed && job.result_document_id) {
						try { placed = await get(fetch, `/sources/${job.result_document_id}`); } catch {}
					}
					const targetFolder = pendingTargetFolders[stagedId];
					if (targetFolder !== undefined) {
						delete pendingTargetFolders[stagedId];
					}
					const targetTag = pendingTargetTags[stagedId];
					if (targetTag !== undefined) {
						delete pendingTargetTags[stagedId];
						if (job.result_document_id) {
							try {
								const currentTopics = placed?.topics ?? [];
								if (!currentTopics.includes(targetTag)) {
									await patch(fetch, `/sources/${job.result_document_id}/topics`, { topics: [...currentTopics, targetTag] });
								}
							} catch {}
						}
					}

					// Smart destination suggestion: intake target folder > Reader suggested_folder > folder_path > keyword match
					let suggested = targetFolder ?? (placed?.suggested_folder || placed?.folder_path || '');
					if (!suggested && placed?.title) {
						const titleLower = placed.title.toLowerCase();
						for (const p of folderPaths) {
							const seg = p.split('/').pop()?.toLowerCase();
							if (seg && seg.length > 3 && titleLower.includes(seg)) {
								suggested = p;
								break;
							}
						}
					}

					if (placed) {
						const docId = placed.id;
						const existingIdx = pendingPlacements.findIndex((p) => p.documentId === docId);
						const aiTopics = (placed.topics ?? []).map((t: string) => t.trim().toLowerCase()).filter(Boolean);
						const initialTags = Array.from(new Set([
							...aiTopics,
							...(targetTag ? [targetTag.trim().toLowerCase()] : [])
						])).filter(Boolean);

						const itemData: PendingPlacement = {
							documentId: docId,
							source: placed,
							title: placed.title,
							filename: placed.original_filename || placed.title,
							currentFolder: placed.folder_path || '',
							suggestedFolder: suggested,
							selectedFolder: suggested,
							isCreatingNewFolder: false,
							newFolderName: '',
							docType: placed.doc_type || '',
							suggestedTags: aiTopics,
							selectedTags: initialTags,
							newTagInput: ''
						};
						if (existingIdx >= 0) {
							pendingPlacements[existingIdx] = itemData;
						} else {
							// Appends to list: if dialog is already open, reactive update adds it in real time
							pendingPlacements = [...pendingPlacements, itemData];
						}
						// Open or keep open placement dialog
						placementDialogOpen = true;
						needsFinalization = new Set([...needsFinalization, placed.id]);
					}

					toast(
						placed
							? `"${placed.title.slice(0, 40)}" finished ingestion — please confirm destination folder and tags.`
							: 'Ingested into the library.'
					);
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

	// Library browser: categories = topics (from /api/coverage, with counts),
	// a kind filter alongside them, and a search box over both. Filtered
	// client-side since the PoC library tops out around a few dozen sources
	// (README "Deliberate PoC limits") and +page.ts already loads up to 200.
	let q = $state('');
	let activeTopic = $state('');

	// Direct instruction: the Library's Files/Folders browsing should
	// feel like macOS Finder. Icon view (the grid Finder opens to by
	// default) and List view, not a separate "Folders" mode — in Finder,
	// folders are just items inside whichever view you're already in.
	let viewMode = $state<'icons' | 'list' | 'columns'>(
		(typeof localStorage !== 'undefined' && (localStorage.getItem('admin-library-view') as any)) || 'icons'
	);
	$effect(() => {
		try { localStorage.setItem('admin-library-view', viewMode); } catch {}
	});

	// Icon and folder size toggle in Icon view (specs/v15/18)
	let iconSize = $state<'large' | 'medium' | 'small'>(
		(typeof localStorage !== 'undefined' && (localStorage.getItem('admin-library-icon-size') as any)) || 'large'
	);
	$effect(() => {
		try { localStorage.setItem('admin-library-icon-size', iconSize); } catch {}
	});

	const tileIconSizes = $derived({
		folder: iconSize === 'small' ? 22 : iconSize === 'medium' ? 30 : 38,
		tag: iconSize === 'small' ? 22 : iconSize === 'medium' ? 30 : 38,
		doc: iconSize === 'small' ? 20 : iconSize === 'medium' ? 28 : 36,
		staged: iconSize === 'small' ? 20 : iconSize === 'medium' ? 28 : 34
	});
	const tileBadgeIconSize = $derived(iconSize === 'small' ? 8 : 10);

	// The quick-access tree sidebar is always there (Icon or List view
	// alike — only the Concept graph has no use for it), collapsible
	// with its own chevron rather than tied to the view toggle.
	let sidebarCollapsed = $state(
		typeof localStorage !== 'undefined' && localStorage.getItem('admin-library-sidebar') === 'collapsed'
	);
	$effect(() => {
		try { localStorage.setItem('admin-library-sidebar', sidebarCollapsed ? 'collapsed' : 'open'); } catch {}
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
	const EXT_ICON: Record<string, string> = {
		pdf: 'pdf',
		jpg: 'image', jpeg: 'image', png: 'image', gif: 'image', webp: 'image', svg: 'image', heic: 'image',
		ppt: 'slide', pptx: 'slide', key: 'slide',
		xls: 'table', xlsx: 'table', csv: 'table',
		mp3: 'audio', wav: 'audio', m4a: 'audio', aac: 'audio',
		mp4: 'video', mov: 'video', webm: 'video', avi: 'video',
		zip: 'archive', rar: 'archive', '7z': 'archive', tar: 'archive', gz: 'archive'
	};
	// A distinct icon per file kind — by extension when there's a real
	// filename, falling back to the doc_type category for sources that
	// never had one (pasted text, a scraped URL).
	function fileIcon(s: any): string {
		// original_media_type (a real MIME type, set for anything actually
		// uploaded) is a far more reliable signal than filename — found
		// live: most sources' own `filename` is empty for anything ingested
		// by paste/URL, and even uploaded files aren't guaranteed a
		// recognizable extension, so this was falling back to the generic
		// file icon far more often than it should have.
		const mime = (s.original_media_type ?? '').toLowerCase();
		if (mime === 'application/pdf') return 'pdf';
		if (mime.startsWith('image/')) return 'image';
		if (mime.startsWith('video/')) return 'video';
		if (mime.startsWith('audio/')) return 'audio';
		if (mime.includes('presentation') || mime.includes('powerpoint')) return 'slide';
		if (mime.includes('spreadsheet') || mime.includes('excel') || mime === 'text/csv') return 'table';
		if (mime.includes('zip') || mime.includes('compressed') || mime.includes('archive')) return 'archive';
		const ext = (s.filename ?? s.original_name ?? '').split('.').pop()?.toLowerCase();
		if (ext && EXT_ICON[ext]) return EXT_ICON[ext];
		if (s.doc_type === 'picture' || s.doc_type === 'chart') return 'image';
		if (s.doc_type === 'presentation') return 'slide';
		return 'file';
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
	// Tree mode's root-level leaf rows (documents with no folder_path) —
	// alongside the top-level folder nodes above, the same split
	// FolderTree's own `docs`/`showDocs` props expect.
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
				nodes: (res.nodes ?? []).map((n: any) => {
					const mentions = Number(n.mentions ?? 0);
					const degree = Number(n.degree ?? 0);
					const documents = Number(n.documents ?? 0);
					const dataScore = mentions + degree + documents;
					// Default node size reduced by 60% (from 6.0px to 2.4px).
					// Dynamic sizing: The more data it holds (mentions, degree, documents),
					// the larger the node is, and vice versa (scaling down to 2.4px).
					const size = 2.4 + Math.min(28, Math.pow(Math.max(0, dataScore - 1), 0.55) * 1.6);
					return {
						id: n.id,
						label: n.name,
						group: n.type,
						degree,
						mentions,
						documents,
						dataScore,
						size
					};
				}),
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

	// Column View: one column per level from the root down through
	// currentPath, each showing that level's siblings — the real Finder
	// behavior where picking a folder in column N reveals its contents as
	// column N+1, while columns to the left keep showing their own
	// siblings so you can jump to a different branch without losing your
	// place. The trailing column (currentPath's own contents) also lists
	// its documents, same as Icon/List view's main pane.
	const folderColumns = $derived.by(() => {
		const segments = currentPath ? currentPath.split('/') : [];
		const cols: { path: string; nodes: TreeNode[] }[] = [{ path: '', nodes: folderTree }];
		let acc = '';
		let levelNodes = folderTree;
		for (const seg of segments) {
			acc = acc ? `${acc}/${seg}` : seg;
			levelNodes = levelNodes.find((n) => n.path === acc)?.children ?? [];
			cols.push({ path: acc, nodes: levelNodes });
		}
		return cols;
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

	// Tags & Categorizations tree — same document dataset, organized by topics/tags as folders
	const tagTree = $derived.by(() => {
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

		let untaggedCount = 0;
		const untaggedDocs: any[] = [];
		for (const s of data.sources ?? []) {
			const topics = (s.topics ?? []).map((t: string) => t.trim().toLowerCase()).filter(Boolean);
			if (!topics.length) {
				untaggedCount++;
				untaggedDocs.push(s);
				continue;
			}
			for (const t of topics) {
				let acc = '';
				for (const seg of t.split('/')) {
					acc = acc ? `${acc}/${seg}` : seg;
					ensure(acc, seg).count++;
				}
				index.get(t)?.docs.push(s);
			}
		}

		for (const t of customTags) {
			let acc = '';
			for (const seg of t.split('/')) {
				acc = acc ? `${acc}/${seg}` : seg;
				ensure(acc, seg);
			}
		}

		if (untaggedCount > 0) {
			const untaggedNode: TreeNode = {
				name: '(Untagged)',
				path: '__untagged__',
				count: untaggedCount,
				children: [],
				docs: untaggedDocs
			};
			roots.push(untaggedNode);
		}

		function sortTree(nodes: TreeNode[]) {
			nodes.sort((a, b) => {
				if (a.path === '__untagged__') return 1;
				if (b.path === '__untagged__') return -1;
				return a.name.localeCompare(b.name);
			});
			for (const n of nodes) {
				n.docs = sortDocs(n.docs);
				sortTree(n.children);
			}
		}
		sortTree(roots);
		return roots;
	});

	const visibleSubtags = $derived.by(() => {
		if (!currentTag) return tagTree;
		return findNode(tagTree, currentTag)?.children ?? [];
	});

	const tagColumns = $derived.by(() => {
		const segments = currentTag && currentTag !== '__untagged__' ? currentTag.split('/') : [];
		const cols: { path: string; nodes: TreeNode[] }[] = [{ path: '', nodes: tagTree }];
		let acc = '';
		let levelNodes = tagTree;
		for (const seg of segments) {
			acc = acc ? `${acc}/${seg}` : seg;
			levelNodes = levelNodes.find((n) => n.path === acc)?.children ?? [];
			cols.push({ path: acc, nodes: levelNodes });
		}
		return cols;
	});

	const tagBreadcrumb = $derived.by(() => {
		if (!currentTag) return [];
		if (currentTag === '__untagged__') return [{ name: '(Untagged)', path: '__untagged__' }];
		const segments = currentTag.split('/');
		let acc = '';
		return segments.map((name) => {
			acc = acc ? `${acc}/${name}` : name;
			return { name, path: acc };
		});
	});

	const allKnownTags = $derived.by(() => {
		const set = new Set<string>();
		for (const s of data.sources ?? []) {
			for (const t of s.topics ?? []) {
				const c = t.trim().toLowerCase();
				if (c) set.add(c);
			}
		}
		for (const t of customTags) {
			set.add(t);
		}
		return Array.from(set).sort();
	});

	// Finder toolbar's own current-folder title + up-one-level button.
	const currentFolderName = $derived(currentPath ? currentPath.split('/').pop()! : 'Library');
	const currentTagName = $derived(
		currentTag ? (currentTag === '__untagged__' ? 'Untagged' : currentTag.split('/').pop()!) : 'All Categories'
	);
	function goUp() {
		if (mainTab === 'library') {
			const parent = currentPath.includes('/') ? currentPath.slice(0, currentPath.lastIndexOf('/')) : '';
			currentPath = parent;
			selectedFolderPath = null;
		} else if (mainTab === 'tags') {
			if (currentTag === '__untagged__') {
				currentTag = '';
			} else {
				const parent = currentTag.includes('/') ? currentTag.slice(0, currentTag.lastIndexOf('/')) : '';
				currentTag = parent;
			}
			selectedTagPath = null;
		}
	}

	// A non-empty search box switches to a flat, library-wide result list
	// (every matching document regardless of which folder it's in) — the
	// same "search this folder vs. search everywhere" split Finder/
	// Nautilus both make, just defaulting to "everywhere" once you've
	// typed something, since not knowing which folder a document is in
	// is exactly why you'd search for it.
	const searching = $derived(q.trim().length > 0);

	// Typing a query also searches *inside* each document's own text, not
	// just its metadata — GET /sources/search-content ranks by relevance
	// (the same chunk vector + full-text indexes Consult's own retrieval
	// uses), so a query that matches no title/tag but does appear in a
	// document's text — or that's a paraphrase of what's actually in
	// there — still surfaces it, in the order it's actually relevant.
	// Debounced, and only hit at all once there's something to search for.
	let contentMatches = $state<any[] | null>(null);
	// document_id -> the endpoint's own highlighted excerpt (already
	// HTML-escaped server-side with only <mark> tags inserted around the
	// matched term) — shown in the Inspector so a content-only match
	// doesn't just silently appear with no explanation of why.
	let contentSnippets = $state<Record<string, string>>({});
	let contentSearchLoading = $state(false);
	let contentSearchTimer: ReturnType<typeof setTimeout>;
	$effect(() => {
		const needle = q.trim();
		clearTimeout(contentSearchTimer);
		if (!needle) {
			contentMatches = null;
			contentSnippets = {};
			contentSearchLoading = false;
			return;
		}
		contentSearchLoading = true;
		contentSearchTimer = setTimeout(async () => {
			try {
				const res = await get(fetch, `/sources/search-content?q=${encodeURIComponent(needle)}&top_k=30`);
				const byId = new Map((data.sources ?? []).map((s: any) => [s.id, s]));
				const hits = res?.matches ?? [];
				// Resolve each hit back to the full, already-loaded source
				// record (doc_type/grade/folder_path/etc.) — the search
				// endpoint only returns id/title/snippet, not a full card.
				contentMatches = hits.map((m: any) => byId.get(m.document_id)).filter((s: any) => s);
				contentSnippets = Object.fromEntries(hits.map((m: any) => [m.document_id, m.snippet]));
			} catch {
				contentMatches = null;
				contentSnippets = {};
			} finally {
				contentSearchLoading = false;
			}
		}, 300);
	});

	const filtered = $derived.by(() => {
		const needle = q.trim().toLowerCase();
		if (searching) {
			// Union of the instant client-side metadata match (title, tags,
			// folder, etc. — zero latency) and the debounced, relevance-
			// ranked content match, deduped by id — content matches keep
			// their own relevance order rather than being re-sorted.
			const clientMatches = (data.sources ?? []).filter((s: any) => {
				const haystack = [s.title, s.summary, s.origin, s.author, s.filename, s.folder_path, s.kind, ...(s.topics ?? [])];
				return haystack.some((v) => (v ?? '').toLowerCase().includes(needle));
			});
			const seen = new Set(clientMatches.map((s: any) => s.id));
			const contentOnly = (contentMatches ?? []).filter((s: any) => !seen.has(s.id));
			return [...sortDocs(clientMatches), ...contentOnly];
		}
		if (mainTab === 'tags') {
			if (!currentTag) {
				const untagged = (data.sources ?? []).filter((s: any) => !(s.topics?.length));
				return sortDocs(untagged);
			}
			if (currentTag === '__untagged__') {
				const untagged = (data.sources ?? []).filter((s: any) => !(s.topics?.length));
				return sortDocs(untagged);
			}
			const matches = (data.sources ?? []).filter((s: any) => {
				const topics = (s.topics ?? []).map((t: string) => t.trim().toLowerCase());
				return topics.some((t: string) => t === currentTag || t.startsWith(currentTag + '/'));
			});
			return sortDocs(matches);
		}
		const matches = (data.sources ?? []).filter((s: any) => {
			if (activeTopic && !(s.topics ?? []).includes(activeTopic)) return false;
			return (s.folder_path || '') === currentPath;
		});
		return sortDocs(matches);
	});

	// A folder's whole contents render at once (infinite scroll within
	// .finder-content's own overflow-y, not a separate scroll region) —
	// no page-by-page pagination, direct instruction.

	// Regrade/delete: PATCH and DELETE /api/sources/{id} always existed on the
	// backend (the pre-rewrite admin page used both, static/app.js) but had no
	// UI in this rewrite — README.md's "a source can be corrected or removed"
	// had no way to do either (specs/v4/04-known-issues.md#h1).
	// Tags (topics) are editable/assignable by an admin — the Reader's
	// suggestion at ingest is only a starting point, same relationship
	// grade/folder already have to their own Reader suggestions.
	let newTagText: Record<string, string> = $state({});

	// Full rebuild: the detail pane shows one document at a time, so
	// every field is just always there — no per-card "Edit details"
	// progressive disclosure needed any more (that was a fix for N
	// cards all being small forms at once; there's only ever one
	// detail pane open now).
	let selectedDocId = $state<string | null>(null);
	// Found live: closing the Inspector (selectedDocId = null) immediately
	// re-triggered the auto-select-first-doc effect below, so the X button
	// looked like it did nothing — it closed and reopened on the same
	// doc in the same tick. This flag distinguishes "nothing selected yet"
	// from "the user explicitly dismissed it"; a fresh folder/search
	// clears it, so landing somewhere new still shows the first result.
	let inspectorDismissed = $state(false);
	$effect(() => {
		currentPath; currentTag; q; mainTab; viewMode;
		inspectorDismissed = false;
	});
	const selectedDoc = $derived(filtered.find((d: any) => d.id === selectedDocId) ?? null);
	$effect(() => {
		if (!selectedDocId && !inspectorDismissed && filtered.length) selectedDocId = filtered[0].id;
	});
	function closeInspector() {
		selectedDocId = null;
		inspectorDismissed = true;
	}

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
	// Real Finder behavior researched before this rebuild (Apple's own
	// HIG): highlight exactly one drop destination at a time while
	// dragging, not every possible target — a single `$state` the
	// currently-hovered folder sets/clears, not a per-element hover
	// style that'd light up several folders if the pointer passed near
	// more than one.
	let dragOverPath = $state<string | null>(null);
	// Finder's own select-vs-open split: a single click selects (shows
	// the inspector / highlights the tile); a folder only navigates on
	// double-click. Previously every click on a folder navigated
	// immediately, with no way to just select one.
	let selectedFolderPath = $state<string | null>(null);

	// External drag-and-drop file upload states
	let contentExternalDragOver = $state(false);
	let sidebarExternalDragOver = $state(false);
	let contentDragDepth = 0;
	let sidebarDragDepth = 0;

	function hasExternalFiles(e: DragEvent): boolean {
		if (draggedId || draggedFolderPath) return false;
		const types = e.dataTransfer?.types;
		return Boolean(types && (types.includes('Files') || types.includes('application/x-moz-file')));
	}

	async function uploadDirectFiles(files: FileList | File[], targetFolder: string = '', targetTag: string = '') {
		if (!files || files.length === 0) return;
		const fileArray = Array.from(files).filter((f) => f && f.size > 0);
		if (fileArray.length === 0) return;

		toast(`Uploading ${fileArray.length} file${fileArray.length === 1 ? '' : 's'}…`);

		for (const file of fileArray) {
			staging = true;
			stageProgress = null;
			try {
				const staged = await chunkedUpload('/sources', file, {}, (p) => (stageProgress = p), 'stage');
				if (staged?.id) {
					if (targetFolder) {
						pendingTargetFolders[staged.id] = targetFolder;
					}
					if (targetTag) {
						pendingTargetTags[staged.id] = targetTag;
					}
					await invalidateAll();
					ingestOne(staged.id);
					toast(`Queued "${file.name}" for ingestion.`);
				}
			} catch (err: any) {
				toast(`Upload failed for "${file.name}": ${err.message}`, 'alert');
			} finally {
				staging = false;
				stageProgress = null;
			}
		}
		await invalidateAll();
	}

	function handleDropOnFolder(targetPath: string, e?: DragEvent) {
		dragOverPath = null;
		contentExternalDragOver = false;
		sidebarExternalDragOver = false;
		contentDragDepth = 0;
		sidebarDragDepth = 0;

		// External OS file drop directly onto this folder
		if (e && hasExternalFiles(e) && e.dataTransfer?.files?.length) {
			e.preventDefault();
			e.stopPropagation();
			uploadDirectFiles(e.dataTransfer.files, targetPath);
			return;
		}

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

	async function handleDropOnTag(targetTag: string, e?: DragEvent) {
		dragOverPath = null;
		contentExternalDragOver = false;
		sidebarExternalDragOver = false;
		contentDragDepth = 0;
		sidebarDragDepth = 0;

		// External OS file drop directly onto this tag
		if (e && hasExternalFiles(e) && e.dataTransfer?.files?.length) {
			e.preventDefault();
			e.stopPropagation();
			uploadDirectFiles(e.dataTransfer.files, '', targetTag === '__untagged__' ? '' : targetTag);
			return;
		}

		if (targetTag === '__untagged__') return;

		// Internal document drop onto a tag/category folder
		if (draggedId) {
			const s = (data.sources ?? []).find((x: any) => x.id === draggedId);
			draggedId = null;
			if (s) {
				const currentTopics = (s.topics ?? []).map((t: string) => t.trim().toLowerCase());
				const cleaned = targetTag.trim().toLowerCase();
				if (!currentTopics.includes(cleaned)) {
					await setTopics(s, [...(s.topics ?? []), cleaned]);
					toast(`Added category "${cleaned}" to "${s.title.slice(0, 30)}".`);
				}
			}
		}
	}

	function onContentDragEnter(e: DragEvent) {
		if (hasExternalFiles(e)) {
			e.preventDefault();
			contentDragDepth++;
			contentExternalDragOver = true;
		}
	}
	function onContentDragOver(e: DragEvent) {
		if (hasExternalFiles(e)) {
			e.preventDefault();
			if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
			contentExternalDragOver = true;
		}
	}
	function onContentDragLeave(e: DragEvent) {
		if (hasExternalFiles(e)) {
			contentDragDepth = Math.max(0, contentDragDepth - 1);
			if (contentDragDepth === 0) {
				contentExternalDragOver = false;
			}
		}
	}
	function onContentDrop(e: DragEvent) {
		contentDragDepth = 0;
		contentExternalDragOver = false;
		if (hasExternalFiles(e) && e.dataTransfer?.files?.length) {
			e.preventDefault();
			e.stopPropagation();
			if (mainTab === 'tags') {
				uploadDirectFiles(e.dataTransfer.files, '', currentTag === '__untagged__' ? '' : currentTag);
			} else {
				uploadDirectFiles(e.dataTransfer.files, currentPath);
			}
		}
	}

	function onSidebarDragEnter(e: DragEvent) {
		if (hasExternalFiles(e)) {
			e.preventDefault();
			sidebarDragDepth++;
			sidebarExternalDragOver = true;
		}
	}
	function onSidebarDragOver(e: DragEvent) {
		if (hasExternalFiles(e)) {
			e.preventDefault();
			if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
			sidebarExternalDragOver = true;
		}
	}
	function onSidebarDragLeave(e: DragEvent) {
		if (hasExternalFiles(e)) {
			sidebarDragDepth = Math.max(0, sidebarDragDepth - 1);
			if (sidebarDragDepth === 0) {
				sidebarExternalDragOver = false;
			}
		}
	}
	function onSidebarDrop(e: DragEvent) {
		sidebarDragDepth = 0;
		sidebarExternalDragOver = false;
		if (hasExternalFiles(e) && e.dataTransfer?.files?.length) {
			e.preventDefault();
			e.stopPropagation();
			uploadDirectFiles(e.dataTransfer.files, '');
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
		'lecture notes', 'protocol', 'picture', 'chart', 'marketing', 'administrative', 'other'
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
	let movingBulk = $state(false);
	let bulkTagOpen = $state(false);
	let bulkTagInput = $state('');
	let deletingBulk = $state(false);

	function askMove(s: any) {
		movingSource = s;
		movingBulk = false;
		movingPath = s.folder_path ?? '';
		movingOpen = true;
	}

	function askBulkMove() {
		if (totalSelectedCount === 0) return;
		movingBulk = true;
		movingSource = null;
		movingPath = currentPath ?? '';
		movingOpen = true;
	}

	function askBulkTag() {
		if (!librarySelected.size) return;
		bulkTagInput = currentTag && currentTag !== '__untagged__' ? currentTag : '';
		bulkTagOpen = true;
	}

	async function confirmBulkTag(e?: Event) {
		if (e) e.preventDefault();
		const tag = bulkTagInput.trim().toLowerCase();
		if (!tag) return;
		const ids = [...librarySelected];
		bulkTagOpen = false;
		try {
			for (const id of ids) {
				const doc = (data.sources ?? []).find((x: any) => x.id === id);
				const existing = doc?.topics ?? [];
				if (!existing.includes(tag)) {
					await patch(fetch, `/sources/${id}/topics`, { topics: [...existing, tag] });
				}
			}
			toast(`Assigned category "${tag}" to ${ids.length} item${ids.length === 1 ? '' : 's'}.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function bulkRemoveTag(tag: string) {
		if (!tag || tag === '__untagged__') return;
		const ids = [...librarySelected];
		if (!ids.length) return;
		try {
			for (const id of ids) {
				const doc = (data.sources ?? []).find((x: any) => x.id === id);
				const existing = doc?.topics ?? [];
				if (existing.includes(tag)) {
					await patch(fetch, `/sources/${id}/topics`, { topics: existing.filter((t: string) => t !== tag) });
				}
			}
			toast(`Removed category "${tag}" from ${ids.length} item${ids.length === 1 ? '' : 's'}.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	function askDeleteBulk() {
		if (totalSelectedCount === 0) return;
		deleting = null;
		deletingBulk = true;
		confirmingDelete = true;
	}

	function onDocClick(e: MouseEvent, s: any) {
		if (e.shiftKey || e.metaKey || e.ctrlKey) {
			toggleLibrarySelected(s.id);
			selectedDocId = s.id;
		} else {
			if (totalSelectedCount > 0 && !librarySelected.has(s.id)) {
				clearAllSelections();
			}
			selectedDocId = s.id;
		}
	}

	function onFolderClick(e: MouseEvent, node: TreeNode) {
		if (e.shiftKey || e.metaKey || e.ctrlKey) {
			toggleFolderSelected(node.path);
			selectedFolderPath = node.path;
		} else {
			if (totalSelectedCount > 0 && !selectedFolderPaths.has(node.path)) {
				clearAllSelections();
			}
			selectedFolderPath = node.path;
		}
	}

	function onTagClick(e: MouseEvent, node: TreeNode) {
		if (e.shiftKey || e.metaKey || e.ctrlKey) {
			toggleTagSelected(node.path);
			selectedTagPath = node.path;
		} else {
			if (totalSelectedCount > 0 && !selectedTagPaths.has(node.path)) {
				clearAllSelections();
			}
			selectedTagPath = node.path;
		}
	}

	// A real floating context menu at the cursor — the same actions the
	// Inspector's own "More actions" menu already offers for a document,
	// not a jump straight to one dialog (Move) the way this used to work.
	let ctxMenu = $state<{ x: number; y: number; kind: 'doc' | 'folder' | 'tag' | 'empty' | 'staged' | 'bulk-doc' | 'bulk'; target: any } | null>(null);
	function openContextMenu(e: MouseEvent, kind: 'doc' | 'folder' | 'tag' | 'empty' | 'staged' | 'bulk-doc' | 'bulk', target: any) {
		e.preventDefault();
		e.stopPropagation();
		const x = Math.min(e.clientX, window.innerWidth - 220);
		const y = Math.min(e.clientY, window.innerHeight - 260);
		ctxMenu = { x, y, kind, target };
	}
	function onDocContextMenu(e: MouseEvent, s: any) {
		if (librarySelected.has(s.id) && totalSelectedCount > 1) {
			openContextMenu(e, 'bulk', { count: totalSelectedCount });
		} else {
			if (!librarySelected.has(s.id)) {
				clearAllSelections();
				librarySelected = new Set([s.id]);
			}
			openContextMenu(e, 'doc', s);
		}
	}
	function onStagedContextMenu(e: MouseEvent, item: any) {
		openContextMenu(e, 'staged', item);
	}
	function onFolderContextMenu(e: MouseEvent, node: TreeNode) {
		if (selectedFolderPaths.has(node.path) && totalSelectedCount > 1) {
			openContextMenu(e, 'bulk', { count: totalSelectedCount });
		} else {
			if (!selectedFolderPaths.has(node.path)) {
				clearAllSelections();
				selectedFolderPaths = new Set([node.path]);
			}
			selectedFolderPath = node.path;
			openContextMenu(e, 'folder', node);
		}
	}
	function onTagContextMenu(e: MouseEvent, node: TreeNode) {
		if (selectedTagPaths.has(node.path) && totalSelectedCount > 1) {
			openContextMenu(e, 'bulk', { count: totalSelectedCount });
		} else {
			if (!selectedTagPaths.has(node.path)) {
				clearAllSelections();
				selectedTagPaths = new Set([node.path]);
			}
			selectedTagPath = node.path;
			openContextMenu(e, 'tag', node);
		}
	}
	function onEmptyContextMenu(e: MouseEvent) {
		if (mainTab !== 'library' && mainTab !== 'tags') return;
		if (totalSelectedCount > 1) {
			openContextMenu(e, 'bulk', { count: totalSelectedCount });
		} else {
			openContextMenu(e, 'empty', null);
		}
	}
	function closeContextMenu() {
		ctxMenu = null;
	}

	function createCategory(name: string) {
		const cleaned = name.trim().toLowerCase();
		if (!cleaned) return;
		const fullPath = currentTag && currentTag !== '__untagged__' ? `${currentTag}/${cleaned}` : cleaned;
		if (!customTags.includes(fullPath)) {
			customTags = [...customTags, fullPath];
			toast(`Created category "${fullPath}".`);
		}
		newCategoryOpen = false;
		newCategoryName = '';
	}

	function askRenameTag(tag: string) {
		if (tag === '__untagged__') return;
		renameTagOld = tag;
		renameTagNew = tag;
		renameTagOpen = true;
	}

	async function confirmRenameTag() {
		const oldTag = renameTagOld;
		const newTag = renameTagNew.trim().toLowerCase();
		if (!newTag || newTag === oldTag) {
			renameTagOpen = false;
			return;
		}
		try {
			const docsToUpdate = (data.sources ?? []).filter((s: any) => (s.topics ?? []).includes(oldTag));
			for (const doc of docsToUpdate) {
				const updated = (doc.topics ?? []).map((t: string) => (t === oldTag ? newTag : t));
				await patch(fetch, `/sources/${doc.id}/topics`, { topics: updated });
			}
			customTags = customTags.map((t) => (t === oldTag ? newTag : t));
			toast(`Renamed category "${oldTag}" to "${newTag}" (${docsToUpdate.length} item${docsToUpdate.length === 1 ? '' : 's'}).`);
			if (currentTag === oldTag) currentTag = newTag;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			renameTagOpen = false;
		}
	}

	async function askDeleteTag(tag: string, count: number) {
		if (tag === '__untagged__') return;
		const confirmed = window.confirm(`Remove category "${tag}" from ${count} document(s)?`);
		if (!confirmed) return;
		try {
			const docsToUpdate = (data.sources ?? []).filter((s: any) => (s.topics ?? []).includes(tag));
			for (const doc of docsToUpdate) {
				const updated = (doc.topics ?? []).filter((t: string) => t !== tag);
				await patch(fetch, `/sources/${doc.id}/topics`, { topics: updated });
			}
			customTags = customTags.filter((t) => t !== tag);
			toast(`Removed category "${tag}".`);
			if (currentTag === tag) currentTag = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function confirmMove(e: Event) {
		e.preventDefault();
		if (movingBulk) {
			const docIds = [...librarySelected];
			const folderList = [...selectedFolderPaths];
			if (!docIds.length && !folderList.length) return;
			try {
				if (docIds.length) {
					await Promise.all(docIds.map((id) => patch(fetch, `/sources/${id}/folder`, { folder_path: movingPath })));
				}
				if (folderList.length) {
					await Promise.all(folderList.map((f) => {
						const folderName = f.split('/').pop() || f;
						const newPath = movingPath ? `${movingPath}/${folderName}` : folderName;
						if (newPath !== f) {
							return post(fetch, '/library/folders/rename', { old_path: f, new_path: newPath });
						}
						return Promise.resolve();
					}));
				}
				const totalMoved = docIds.length + folderList.length;
				toast(`Moved ${totalMoved} item${totalMoved === 1 ? '' : 's'} to "${movingPath || '(root)'}".`);
				clearAllSelections();
				movingOpen = false;
				movingBulk = false;
				await invalidateAll();
			} catch (err: any) {
				toast(err.message, 'alert');
			}
			return;
		}
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
			// Dismiss any pending placements for docs inside this folder
			for (const p of pendingPlacements) {
				if (p.source?.folder_path === path || p.source?.folder_path?.startsWith(`${path}/`)) {
					dismissFinalization(p.documentId);
				}
			}
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

	// Multi-selection state across documents and folders (specs/v15/14, specs/v15/17)
	let librarySelected = $state<Set<string>>(new Set());
	let selectedFolderPaths = $state<Set<string>>(new Set());
	let selectedTagPaths = $state<Set<string>>(new Set());

	const totalSelectedCount = $derived(
		librarySelected.size +
		(mainTab === 'tags' ? selectedTagPaths.size : selectedFolderPaths.size)
	);

	function toggleLibrarySelected(id: string) {
		const next = new Set(librarySelected);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		librarySelected = next;
	}

	function toggleFolderSelected(path: string) {
		const next = new Set(selectedFolderPaths);
		if (next.has(path)) next.delete(path);
		else next.add(path);
		selectedFolderPaths = next;
	}

	function toggleTagSelected(path: string) {
		const next = new Set(selectedTagPaths);
		if (next.has(path)) next.delete(path);
		else next.add(path);
		selectedTagPaths = next;
	}

	function clearAllSelections() {
		librarySelected = new Set();
		selectedFolderPaths = new Set();
		selectedTagPaths = new Set();
		selectedDocId = null;
		selectedFolderPath = null;
		selectedTagPath = null;
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
		const docIds = [...librarySelected];
		const folderList = [...selectedFolderPaths];
		if (!docIds.length && !folderList.length) return;
		try {
			if (docIds.length) {
				await Promise.all(docIds.map((id) => patch(fetch, `/sources/${id}/privacy`, { is_private: isPrivate })));
			}
			if (folderList.length) {
				await Promise.all(folderList.map((f) => post(fetch, '/library/folders/privacy', { folder_path: f, is_private: isPrivate })));
			}
			const total = docIds.length + folderList.length;
			toast(`${total} item${total === 1 ? '' : 's'} set to ${isPrivate ? 'private' : 'public'}.`);
			clearAllSelections();
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
		deletingBulk = false;
		confirmingDelete = true;
	}

	async function confirmDelete() {
		if (deletingBulk) {
			const docIds = [...librarySelected];
			const folderList = [...selectedFolderPaths];
			const tagList = [...selectedTagPaths];
			confirmingDelete = false;
			deletingBulk = false;
			try {
				if (docIds.length) {
					for (const id of docIds) dismissFinalization(id);
					await Promise.all(docIds.map((id) => del(fetch, `/sources/${id}`)));
				}
				if (folderList.length) {
					await Promise.all(folderList.map((f) => post(fetch, '/library/folders/delete', { folder_path: f })));
				}
				if (tagList.length) {
					for (const tag of tagList) {
						if (tag === '__untagged__') continue;
						const docsToUpdate = (data.sources ?? []).filter((s: any) => (s.topics ?? []).includes(tag));
						for (const doc of docsToUpdate) {
							const updated = (doc.topics ?? []).filter((t: string) => t !== tag);
							await patch(fetch, `/sources/${doc.id}/topics`, { topics: updated });
						}
						customTags = customTags.filter((t) => t !== tag);
					}
				}
				const totalDeleted = docIds.length + folderList.length + tagList.length;
				toast(`Removed ${totalDeleted} item${totalDeleted === 1 ? '' : 's'} from library.`);
				clearAllSelections();
				await invalidateAll();
			} catch (err: any) {
				toast(err.message, 'alert');
			}
			return;
		}
		if (!deleting) return;
		const s = deleting;
		dismissFinalization(s.id);
		confirmingDelete = false;
		try {
			await del(fetch, `/sources/${s.id}`);
			toast('Source removed from the library.');
			if (selectedDocId === s.id) selectedDocId = null;
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	// --- Upload tab: drag-and-drop with multi-file support and PDF preview ---
	let dragOver = $state(false);
	let selectedFiles = $state<File[]>([]);
	let previewUrls: Record<string, string> = {};
	let multiUploadProgress = $state<{ current: number; total: number; filename: string } | null>(null);

	function addFiles(files: FileList | File[] | null) {
		if (!files) return;
		const incoming = Array.from(files).filter((f) => f && f.size > 0);
		if (!incoming.length) return;
		const existingKeys = new Set(selectedFiles.map((f) => `${f.name}:${f.size}`));
		const toAdd = incoming.filter((f) => !existingKeys.has(`${f.name}:${f.size}`));
		selectedFiles = [...selectedFiles, ...toAdd];
		for (const f of toAdd) {
			if (f.type === 'application/pdf' && !previewUrls[f.name]) {
				previewUrls[f.name] = URL.createObjectURL(f);
			}
		}
	}

	function removeFile(index: number) {
		const removed = selectedFiles[index];
		if (removed && previewUrls[removed.name]) {
			URL.revokeObjectURL(previewUrls[removed.name]);
			delete previewUrls[removed.name];
		}
		selectedFiles = selectedFiles.filter((_, i) => i !== index);
	}

	function clearSelectedFiles() {
		for (const url of Object.values(previewUrls)) {
			URL.revokeObjectURL(url);
		}
		previewUrls = {};
		selectedFiles = [];
		if (fileInput) fileInput.value = '';
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		if (e.dataTransfer?.files?.length) {
			addFiles(e.dataTransfer.files);
		}
	}

	function onFileInputChange(e: Event) {
		const files = (e.target as HTMLInputElement).files;
		if (files?.length) {
			addFiles(files);
		}
	}

	async function stageFiles() {
		if (!selectedFiles.length) return;
		staging = true;
		stageProgress = null;
		const totalCount = selectedFiles.length;
		const targetFolder = currentPath;
		const targetTag = mainTab === 'tags' && currentTag && currentTag !== '__untagged__' ? currentTag : '';

		toast(`Uploading ${totalCount} file${totalCount === 1 ? '' : 's'}…`);

		try {
			for (let i = 0; i < totalCount; i++) {
				const file = selectedFiles[i];
				multiUploadProgress = { current: i + 1, total: totalCount, filename: file.name };
				try {
					const staged = await chunkedUpload('/sources', file, {}, (p) => (stageProgress = p), 'stage');
					if (staged?.id) {
						if (targetFolder) {
							pendingTargetFolders[staged.id] = targetFolder;
						}
						if (targetTag) {
							pendingTargetTags[staged.id] = targetTag;
						}
						await invalidateAll();
						ingestOne(staged.id);
					}
				} catch (err: any) {
					toast(`Upload failed for "${file.name}": ${err.message}`, 'alert');
				}
			}
			clearSelectedFiles();
			ingestOpen = false;
			await invalidateAll();
			toast(`Successfully queued ${totalCount} file${totalCount === 1 ? '' : 's'} for ingestion.`);
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			staging = false;
			stageProgress = null;
			multiUploadProgress = null;
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

	async function stopIngesting(stagedId: string) {
		if (pollTimers[stagedId]) {
			clearInterval(pollTimers[stagedId]);
			delete pollTimers[stagedId];
		}
		try {
			await post(fetch, `/staged/${stagedId}/stop`, {});
			jobsByStagedId = {
				...jobsByStagedId,
				[stagedId]: { status: 'error', step: 'error', error_message: 'Ingestion stopped by user.' }
			};
			toast('Ingestion stopped.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function removeStagedFile(stagedId: string) {
		if (pollTimers[stagedId]) {
			clearInterval(pollTimers[stagedId]);
			delete pollTimers[stagedId];
		}
		delete pendingTargetFolders[stagedId];
		delete pendingTargetTags[stagedId];
		try {
			await del(fetch, `/staged/${stagedId}`);
			const next = { ...jobsByStagedId };
			delete next[stagedId];
			jobsByStagedId = next;
			toast('File removed.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		}
	}

	async function discardStaged(id: string) {
		await removeStagedFile(id);
	}

	function isStagedVisible(item: any): boolean {
		if (searching) return false;
		if (mainTab === 'library') {
			const target = pendingTargetFolders[item.id];
			if (currentPath) {
				return target === currentPath;
			}
			return !target || target === '';
		}
		if (mainTab === 'tags') {
			const target = pendingTargetTags[item.id];
			if (currentTag && currentTag !== '__untagged__') {
				return target === currentTag;
			}
			return !target || target === '';
		}
		return false;
	}

	let finderContentEl = $state<HTMLDivElement | null>(null);
	let isMarqueeSelecting = $state(false);
	let marqueeActive = $state(false);
	let marqueeStart = $state<{ x: number; y: number }>({ x: 0, y: 0 });
	let marqueeCurrent = $state<{ x: number; y: number }>({ x: 0, y: 0 });
	let marqueeInitialDocs = $state<Set<string>>(new Set());
	let marqueeInitialFolders = $state<Set<string>>(new Set());
	let marqueeInitialTags = $state<Set<string>>(new Set());

	function onContentMouseDown(e: MouseEvent) {
		if (e.button !== 0) return;
		if (mainTab !== 'library' && mainTab !== 'tags') return;

		const target = e.target as HTMLElement | null;
		if (!target) return;

		// Don't start marquee if user clicked on an interactive control
		if (target.closest('button, a, input, select, textarea, label, [role="button"], .staged-pill-btn, .staged-table-btn, .fchip, .crumb, .badge-tag')) {
			return;
		}
		if (target.closest('.finder-sidebar, .finder-toolbar, .finder-path-bar, .status-row')) {
			return;
		}

		isMarqueeSelecting = true;
		marqueeActive = false;
		marqueeStart = { x: e.clientX, y: e.clientY };
		marqueeCurrent = { x: e.clientX, y: e.clientY };
		const isAdditive = e.shiftKey || e.metaKey || e.ctrlKey;
		marqueeInitialDocs = isAdditive ? new Set(librarySelected) : new Set();
		marqueeInitialFolders = isAdditive ? new Set(selectedFolderPaths) : new Set();
		marqueeInitialTags = isAdditive ? new Set(selectedTagPaths) : new Set();
	}

	function onWindowMouseMove(e: MouseEvent) {
		if (!isMarqueeSelecting) return;

		marqueeCurrent = { x: e.clientX, y: e.clientY };
		const dx = marqueeCurrent.x - marqueeStart.x;
		const dy = marqueeCurrent.y - marqueeStart.y;

		if (!marqueeActive && Math.hypot(dx, dy) > 4) {
			marqueeActive = true;
		}

		if (marqueeActive && finderContentEl) {
			const boxLeft = Math.min(marqueeStart.x, marqueeCurrent.x);
			const boxTop = Math.min(marqueeStart.y, marqueeCurrent.y);
			const boxRight = Math.max(marqueeStart.x, marqueeCurrent.x);
			const boxBottom = Math.max(marqueeStart.y, marqueeCurrent.y);

			const selectableItems = finderContentEl.querySelectorAll('[data-doc-id], [data-folder-path], [data-tag-path]');
			const nextDocs = new Set<string>(marqueeInitialDocs);
			const nextFolders = new Set<string>(marqueeInitialFolders);
			const nextTags = new Set<string>(marqueeInitialTags);

			selectableItems.forEach((el) => {
				const docId = el.getAttribute('data-doc-id');
				const folderPath = el.getAttribute('data-folder-path');
				const tagPath = el.getAttribute('data-tag-path');
				const rect = el.getBoundingClientRect();
				const intersects = !(
					rect.right < boxLeft ||
					rect.left > boxRight ||
					rect.bottom < boxTop ||
					rect.top > boxBottom
				);

				if (docId) {
					if (intersects) nextDocs.add(docId);
					else if (!marqueeInitialDocs.has(docId)) nextDocs.delete(docId);
				} else if (folderPath) {
					if (intersects) nextFolders.add(folderPath);
					else if (!marqueeInitialFolders.has(folderPath)) nextFolders.delete(folderPath);
				} else if (tagPath) {
					if (intersects) nextTags.add(tagPath);
					else if (!marqueeInitialTags.has(tagPath)) nextTags.delete(tagPath);
				}
			});

			librarySelected = nextDocs;
			selectedFolderPaths = nextFolders;
			selectedTagPaths = nextTags;
		}
	}

	function onWindowMouseUp(e: MouseEvent) {
		if (!isMarqueeSelecting) return;

		if (!marqueeActive) {
			if (!e.shiftKey && !e.metaKey && !e.ctrlKey) {
				const target = e.target as HTMLElement | null;
				if (target && !target.closest('button, a, input, select, textarea, label, [data-doc-id], [data-folder-path], [data-tag-path]')) {
					clearAllSelections();
				}
			}
		}

		isMarqueeSelecting = false;
		marqueeActive = false;
	}
</script>

<svelte:window onmousemove={onWindowMouseMove} onmouseup={onWindowMouseUp} />
<svelte:head><title>Library — Admin portal</title></svelte:head>

<!-- Complete rework, grounded in Apple's own Finder/HIG patterns (not
     iterated from the prior list+detail version): a real toolbar
     (back button, folder title, Icon/List view toggle, search), a
     Finder path bar, an Icon View grid with native drag-and-drop and
     a single highlighted drop target at a time (per HIG — "highlight
     one destination, not every possible one"), select-vs-open
     (single click selects, double-click opens a folder), and an
     Inspector panel that only appears once something is selected
     instead of a permanently-reserved half-width pane. -->
<div class="finder">
	<div class="detail-head finder-toolbar">
		<div class="head-title">
			{#if (currentPath && mainTab === 'library') || (currentTag && mainTab === 'tags')}
				<button class="back-nav-btn" onclick={goUp} title="Back" aria-label="Up one level">
					<Icon name="chevron" size={15} />
				</button>
			{/if}
			<span class="head-ico" aria-hidden="true"><Icon name={mainTab === 'graph' ? 'globe' : mainTab === 'tags' ? 'tag' : 'book'} size={18} /></span>
			<div>
				<h1>{mainTab === 'graph' ? 'Concept graph' : mainTab === 'tags' ? currentTagName : currentFolderName}</h1>
				<p>{mainTab === 'graph' ? 'Explore entities, clusters, and knowledge connections' : mainTab === 'tags' ? (currentTag ? `Category · ${currentTag === '__untagged__' ? 'Untagged' : currentTag}` : 'Organize documents by tags and categories') : currentPath ? `Folder · ${currentPath}` : 'Manage knowledge base resources and folders'}</p>
			</div>
		</div>
		<div class="tb-actions">
			<div class="window-switcher" role="tablist" aria-label="Library organization view">
				<button
					class="ws-btn"
					class:active={mainTab === 'library'}
					onclick={() => { mainTab = 'library'; }}
					role="tab"
					aria-selected={mainTab === 'library'}
					title="Folders view"
				>
					<Icon name="folder" size={13} />
					<span>Folders</span>
				</button>
				<button
					class="ws-btn"
					class:active={mainTab === 'tags'}
					onclick={() => { mainTab = 'tags'; }}
					role="tab"
					aria-selected={mainTab === 'tags'}
					title="Tags & Categories view"
				>
					<Icon name="tag" size={13} />
					<span class="ws-label-full">Tags & Categories</span>
					<span class="ws-label-short">Tags</span>
				</button>
				<button
					class="ws-btn"
					class:active={mainTab === 'graph'}
					onclick={() => { mainTab = 'graph'; }}
					role="tab"
					aria-selected={mainTab === 'graph'}
					title="Concept graph"
				>
					<Icon name="globe" size={13} />
					<span>Graph</span>
				</button>
			</div>
			{#if mainTab === 'library' || mainTab === 'tags'}
				<div class="tb-view-toggle" role="group" aria-label="View">
					<button class:on={viewMode === 'icons'} onclick={() => (viewMode = 'icons')} title="Icon View"><Icon name="grid" size={15} /></button>
					<button class:on={viewMode === 'list'} onclick={() => (viewMode = 'list')} title="List View"><Icon name="list" size={15} /></button>
					<button class:on={viewMode === 'columns'} onclick={() => (viewMode = 'columns')} title="Column View"><Icon name="columns" size={15} /></button>
				</div>
				<div class="tb-view-toggle tb-size-toggle" role="group" aria-label="Icon and folder size">
					<button
						class="size-toggle-btn"
						class:on={iconSize === 'small'}
						onclick={() => (iconSize = 'small')}
						title="Small icons"
						aria-label="Small icons"
					>
						<Icon name="size-small" size={15} />
					</button>
					<button
						class="size-toggle-btn"
						class:on={iconSize === 'medium'}
						onclick={() => (iconSize = 'medium')}
						title="Medium icons"
						aria-label="Medium icons"
					>
						<Icon name="size-medium" size={15} />
					</button>
					<button
						class="size-toggle-btn"
						class:on={iconSize === 'large'}
						onclick={() => (iconSize = 'large')}
						title="Large icons (current)"
						aria-label="Large icons (current)"
					>
						<Icon name="size-large" size={15} />
					</button>
				</div>
				<Menu label="Sort" icon="sort">
					{#snippet items()}
						<button onclick={() => (sortBy = 'title')} class="menu-choice" class:menu-active={sortBy === 'title'}>Name</button>
						<button onclick={() => (sortBy = 'created_at')} class="menu-choice" class:menu-active={sortBy === 'created_at'}>Date ingested</button>
						<button onclick={() => (sortDir = sortDir === 'asc' ? 'desc' : 'asc')}>
							<Icon name="chevron" size={14} />{sortDir === 'asc' ? 'Ascending' : 'Descending'}
						</button>
					{/snippet}
				</Menu>
				<div class="tb-search">
					<Icon name="search" size={13} />
					<input type="search" placeholder={mainTab === 'tags' ? "Search categories & docs..." : "Search library..."} bind:value={q} aria-label="Search the library" />
					{#if contentSearchLoading}<Spinner size={11} />{/if}
					{#if q}<button class="search-clear" onclick={() => { q = ''; }} aria-label="Clear search">&times;</button>{/if}
				</div>
			{/if}
			{#if pendingPlacements.length > 0}
				<button
					type="button"
					class="tb-placement-notify"
					class:active={placementDialogOpen}
					onclick={() => (placementDialogOpen = true)}
					title="{pendingPlacements.length} file{pendingPlacements.length === 1 ? '' : 's'} waiting for folder placement"
					aria-label="{pendingPlacements.length} file{pendingPlacements.length === 1 ? '' : 's'} waiting for folder placement"
				>
					<span class="notify-icon-wrap">
						<Icon name="bell" size={14} />
						<span class="notify-ping"></span>
					</span>
					<span class="notify-label">Placement needed</span>
					<span class="notify-count">{pendingPlacements.length}</span>
				</button>
			{/if}
			<Button variant="filled" onclick={() => (ingestOpen = true)}><Icon name="plus" size={14} />Add resources</Button>
			<Menu label="More">
				{#snippet items()}
					{#if mainTab === 'library'}<button onclick={() => { newFolderName = ''; newFolderOpen = true; }}><Icon name="folder" size={14} />New folder</button>{/if}
					{#if mainTab === 'tags'}<button onclick={() => { newCategoryName = ''; newCategoryOpen = true; }}><Icon name="tag" size={14} />New category</button>{/if}
					<button onclick={() => { maintenanceKind = 'relink'; maintenanceOpen = true; }}><Icon name="refresh" size={14} />Relink unlinked</button>
					<button onclick={() => { maintenanceKind = 'consolidate'; maintenanceOpen = true; }}><Icon name="check" size={14} />Consolidate entities</button>
				{/snippet}
			</Menu>
		</div>
	</div>

	{#if maintenanceProgress && (maintenanceProgress.status === 'running' || maintenanceProgress.status === 'done' || maintenanceProgress.status === 'error')}
		<div class="maintenance-bar" class:done={maintenanceProgress.status === 'done'} class:error={maintenanceProgress.status === 'error'}>
			<div class="maintenance-bar-left">
				<span class="m-icon" class:spin={maintenanceProgress.status === 'running'}>
					<Icon name={maintenanceProgress.status === 'done' ? 'check' : maintenanceProgress.kind === 'relink' ? 'refresh' : 'sparkles'} size={15} />
				</span>
				<div class="m-info">
					<div class="m-title-row">
						<span class="m-kind-badge">{maintenanceProgress.kind === 'relink' ? 'Relinking Graph' : 'Consolidating Entities'}</span>
						<span class="m-step-text">{maintenanceProgress.detail || 'Working…'}</span>
					</div>
					<div class="m-track" role="progressbar" aria-valuenow={maintenanceProgress.percentage} aria-valuemin={0} aria-valuemax={100}>
						<div class="m-fill" style="width: {maintenanceProgress.percentage}%"></div>
					</div>
				</div>
			</div>
			<div class="m-actions">
				<span class="m-percentage">{maintenanceProgress.percentage}%</span>
				{#if maintenanceProgress.status === 'running'}
					<button type="button" class="m-btn-details" onclick={() => { maintenanceKind = maintenanceProgress!.kind; maintenanceOpen = true; }}>
						Details
					</button>
					<button type="button" class="m-btn-stop" onclick={stopMaintenanceTask} title="Stop maintenance task">
						Stop
					</button>
				{:else}
					<button type="button" class="m-btn-dismiss" onclick={() => { maintenanceProgress = null; }} aria-label="Dismiss">
						&times;
					</button>
				{/if}
			</div>
		</div>
	{/if}

	{#if mainTab === 'library' && !searching}
		<!-- Finder's path bar: a pill-shaped bar, a folder icon per
		     segment, chevrons pointing right between them — also itself
		     a drop target per segment, so dragging a tile onto an
		     ancestor folder works the way it does in a real Finder
		     window. -->
		<nav class="pathbar" aria-label="Folder path">
			<button
				class="crumb" class:drag-target={dragOverPath === ''}
				onclick={() => { currentPath = ''; selectedFolderPath = null; }}
				ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = ''; }}
				ondragleave={() => (dragOverPath = null)}
				ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnFolder('', e); }}
				disabled={!currentPath}
			><Icon name="folder" size={12} />Library</button>
			{#each breadcrumb as crumb, i (crumb.path)}
				<Icon name="chevron" size={10} />
				<button
					class="crumb" class:drag-target={dragOverPath === crumb.path}
					onclick={() => { currentPath = crumb.path; selectedFolderPath = null; }}
					ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = crumb.path; }}
					ondragleave={() => (dragOverPath = null)}
					ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnFolder(crumb.path, e); }}
					disabled={i === breadcrumb.length - 1}
				><Icon name="folder" size={12} />{crumb.name}</button>
			{/each}
		</nav>
	{:else if mainTab === 'tags' && !searching}
		<nav class="pathbar" aria-label="Category path">
			<button
				class="crumb" class:drag-target={dragOverPath === ''}
				onclick={() => { currentTag = ''; selectedTagPath = null; }}
				ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = ''; }}
				ondragleave={() => (dragOverPath = null)}
				ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnTag('', e); }}
				disabled={!currentTag}
			><Icon name="tag" size={12} />Categories</button>
			{#each tagBreadcrumb as crumb, i (crumb.path)}
				<Icon name="chevron" size={10} />
				<button
					class="crumb" class:drag-target={dragOverPath === crumb.path}
					onclick={() => { currentTag = crumb.path; selectedTagPath = null; }}
					ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = crumb.path; }}
					ondragleave={() => (dragOverPath = null)}
					ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnTag(crumb.path, e); }}
					disabled={i === tagBreadcrumb.length - 1}
				><Icon name="tag" size={12} />{crumb.name}</button>
			{/each}
		</nav>
	{/if}

	{#if mainTab === 'library' || mainTab === 'tags'}
		{#if (data.staged?.length ?? 0) > 0 || (queueStats?.queued_count ?? 0) > 0 || (queueStats?.processing_count ?? 0) > 0 || totalSelectedCount > 0}
			<div class="status-row">
				{#if totalSelectedCount > 0}
					<span class="hint">
						{#if selectedFolderPaths.size > 0 && librarySelected.size > 0}
							{totalSelectedCount} selected ({selectedFolderPaths.size} folders, {librarySelected.size} docs)
						{:else if selectedFolderPaths.size > 0}
							{selectedFolderPaths.size} folder{selectedFolderPaths.size === 1 ? '' : 's'} selected
						{:else if selectedTagPaths.size > 0}
							{selectedTagPaths.size} categor{selectedTagPaths.size === 1 ? 'y' : 'ies'} selected
						{:else}
							{librarySelected.size} selected
						{/if}
					</span>
					<button class="status-action" onclick={askBulkMove} title="Move to folder"><Icon name="folder" size={13} /></button>
					{#if librarySelected.size > 0}
						<button class="status-action" onclick={askBulkTag} title="Assign category"><Icon name="tag" size={13} /></button>
					{/if}
					{#if mainTab !== 'tags'}
						<button class="status-action" onclick={() => setPrivateBulk(true)} title="Make private"><Icon name="lock" size={13} /></button>
						<button class="status-action" onclick={() => setPrivateBulk(false)} title="Make public"><Icon name="unlock" size={13} /></button>
					{/if}
					<button class="status-action danger" onclick={askDeleteBulk} title="Remove selected from library"><Icon name="trash" size={13} /></button>
					<button class="status-action" onclick={clearAllSelections} title="Clear selection"><Icon name="x" size={13} /></button>
				{:else}
					<span class="hint">
						{(queueStats?.queued_count ?? 0) + (queueStats?.processing_count ?? 0)} in queue
						{#if queueStats?.processing_count}({queueStats.processing_count} processing){/if}
						{#if erroredStagedIds.length}
							· <button class="retry-link" onclick={retryAll} disabled={retryingAll}>retry {erroredStagedIds.length} failed</button>
						{/if}
					</span>
				{/if}
			</div>
		{/if}
	{/if}

	<div class="finder-body">
		{#if (mainTab === 'library' || mainTab === 'tags') && !searching}
			<!-- Finder's left sidebar: a permanent quick-access tree
			     (favorites/locations in a real Finder window) — present
			     in Icon or List view alike (only the Concept graph has no
			     use for it), collapsible with its own chevron rather than
			     tied to the view toggle. -->
			{#if sidebarCollapsed}
				<button class="sidebar-expand" onclick={() => (sidebarCollapsed = false)} title="Show sidebar" aria-label="Show sidebar">
					<Icon name="chevron" size={13} />
				</button>
			{:else}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<aside
					class="finder-sidebar"
					class:external-dragover={sidebarExternalDragOver}
					oncontextmenu={onEmptyContextMenu}
					ondragenter={onSidebarDragEnter}
					ondragover={onSidebarDragOver}
					ondragleave={onSidebarDragLeave}
					ondrop={onSidebarDrop}
				>
					{#if mainTab === 'library'}
						<div class="sidebar-head">
							<button
								class="tree-root"
								class:active={!currentPath}
								ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; }}
								ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnFolder('', e); }}
								onclick={() => { currentPath = ''; selectedFolderPath = null; }}
							>
								<Icon name="folder" size={14} /> Library <span class="row-sub">{data.sources.length}</span>
							</button>
							<button class="sidebar-collapse" onclick={() => (sidebarCollapsed = true)} title="Hide sidebar" aria-label="Hide sidebar">
								<Icon name="chevron" size={13} />
							</button>
						</div>
						<FolderTree
							nodes={folderTree}
							activePath={currentPath}
							onSelect={(path) => { currentPath = path; selectedFolderPath = null; }}
							onDrop={handleDropOnFolder}
							onRename={askRenameFolder}
							onPrivatize={setFolderPrivate}
							onDelete={(path, count) => askDeleteFolder(path, count)}
							onContextMenu={onFolderContextMenu}
						/>
					{:else}
						<div class="sidebar-head">
							<button
								class="tree-root"
								class:active={!currentTag}
								ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; }}
								ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnTag('', e); }}
								onclick={() => { currentTag = ''; selectedTagPath = null; }}
							>
								<Icon name="tag" size={14} /> Categories <span class="row-sub">{data.sources.length}</span>
							</button>
							<button class="sidebar-collapse" onclick={() => (sidebarCollapsed = true)} title="Hide sidebar" aria-label="Hide sidebar">
								<Icon name="chevron" size={13} />
							</button>
						</div>
						<FolderTree
							nodes={tagTree}
							activePath={currentTag}
							icon="tag"
							onSelect={(path) => { currentTag = path; selectedTagPath = null; }}
							onDrop={handleDropOnTag}
							onRename={askRenameTag}
							onDelete={(path, count) => askDeleteTag(path, count)}
							onContextMenu={onTagContextMenu}
						/>
					{/if}
					{#if sidebarExternalDragOver}
						<div class="drop-overlay sidebar-overlay">
							<div class="drop-pill">
								<Icon name="upload" size={14} />
								<span>Drop to upload to {mainTab === 'tags' ? 'Categories' : 'Library'}</span>
							</div>
						</div>
					{/if}
				</aside>
			{/if}
		{/if}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="finder-content size-{iconSize}"
			class:grid-mode={(mainTab === 'library' || mainTab === 'tags') && viewMode === 'icons'}
			class:external-dragover={contentExternalDragOver}
			class:marquee-active={isMarqueeSelecting && marqueeActive}
			bind:this={finderContentEl}
			onmousedown={onContentMouseDown}
			oncontextmenu={onEmptyContextMenu}
			ondragenter={onContentDragEnter}
			ondragover={onContentDragOver}
			ondragleave={onContentDragLeave}
			ondrop={onContentDrop}
		>
			{#if isMarqueeSelecting && marqueeActive}
				{@const boxLeft = Math.min(marqueeStart.x, marqueeCurrent.x)}
				{@const boxTop = Math.min(marqueeStart.y, marqueeCurrent.y)}
				{@const boxWidth = Math.abs(marqueeCurrent.x - marqueeStart.x)}
				{@const boxHeight = Math.abs(marqueeCurrent.y - marqueeStart.y)}
				<div
					class="marquee-selection-box"
					style="left: {boxLeft}px; top: {boxTop}px; width: {boxWidth}px; height: {boxHeight}px;"
				></div>
			{/if}
			{#if contentExternalDragOver}
				<div class="drop-overlay">
					<div class="drop-pill">
						<Icon name="upload" size={20} />
						<span>Drop files to upload to {mainTab === 'tags' ? (currentTag ? `category "${currentTag === '__untagged__' ? 'Untagged' : currentTag}"` : 'Categories') : currentPath ? `"${currentPath}"` : 'Library'}</span>
					</div>
				</div>
			{/if}
			{#if mainTab === 'graph'}
				<div class="graph-pane">
					{#if data.graph}
						<p class="hint graph-stats">{data.graph.entities ?? 0} concepts · {data.graph.mentions ?? 0} links · {(data.graph.unlinked ?? []).length} unlinked</p>
					{/if}
					{#if conceptGraphLoading}
						<p class="hint"><Spinner size={13} /> Loading the concept graph…</p>
					{:else}
						<GraphView nodes={conceptGraph?.nodes ?? []} edges={conceptGraph?.edges ?? []} />
					{/if}
				</div>
			{:else if viewMode === 'icons'}
				<div class="icon-grid size-{iconSize}">
					{#if !searching}
						{#if mainTab === 'library'}
							{#each visibleSubfolders as node (node.path)}
								<button
									class="icon-tile folder-tile"
									class:on={selectedFolderPath === node.path}
									class:selected={selectedFolderPaths.has(node.path)}
									data-folder-path={node.path}
									draggable="true"
									ondragstart={() => (draggedFolderPath = node.path)}
									ondragend={() => { draggedFolderPath = null; dragOverPath = null; }}
									ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = node.path; }}
									ondragleave={() => (dragOverPath = null)}
									ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnFolder(node.path, e); }}
									onclick={(e) => onFolderClick(e, node)}
									ondblclick={() => { currentPath = node.path; clearAllSelections(); }}
									oncontextmenu={(e) => onFolderContextMenu(e, node)}
								>
									<div class="tile-header-bar folder-header-bar">
										<span class="file-ext-tag folder-tag">DIR</span>
										<input
											type="checkbox"
											class="tile-select-check"
											checked={selectedFolderPaths.has(node.path)}
											onclick={(e) => e.stopPropagation()}
											onchange={() => toggleFolderSelected(node.path)}
											aria-label="Select folder {node.name}"
										/>
									</div>
									<div class="tile-art folder-art">
										<Icon name="folder" size={tileIconSizes.folder} />
									</div>
									<span class="tile-label">{node.name}</span>
									<span class="tile-meta-pill">{node.count} {node.count === 1 ? 'item' : 'items'}</span>
								</button>
							{/each}
						{:else}
							{#each visibleSubtags as node (node.path)}
								<button
									class="icon-tile folder-tile tag-tile"
									class:on={selectedTagPath === node.path}
									class:selected={selectedTagPaths.has(node.path)}
									data-tag-path={node.path}
									draggable="false"
									ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = node.path; }}
									ondragleave={() => (dragOverPath = null)}
									ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnTag(node.path, e); }}
									onclick={(e) => onTagClick(e, node)}
									ondblclick={() => { currentTag = node.path; clearAllSelections(); }}
									oncontextmenu={(e) => onTagContextMenu(e, node)}
								>
									<div class="tile-header-bar folder-header-bar">
										<span class="file-ext-tag tag-ext-tag">TAG</span>
										<input
											type="checkbox"
											class="tile-select-check"
											checked={selectedTagPaths.has(node.path)}
											onclick={(e) => e.stopPropagation()}
											onchange={() => toggleTagSelected(node.path)}
											aria-label="Select category {node.name}"
										/>
									</div>
									<div class="tile-art folder-art tag-art">
										<Icon name="tag" size={tileIconSizes.tag} />
									</div>
									<span class="tile-label">{node.name}</span>
									<span class="tile-meta-pill">{node.count} {node.count === 1 ? 'item' : 'items'}</span>
								</button>
							{/each}
						{/if}
					{/if}
					{#if !searching}
						{#each (data.staged ?? []).filter(isStagedVisible) as item (item.id)}
							<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
							<div
								class="icon-tile staged-tile"
								class:error={jobsByStagedId[item.id]?.status === 'error'}
								oncontextmenu={(e) => onStagedContextMenu(e, item)}
								role="region"
								aria-label="Ingesting {item.filename ?? 'file'}"
								tabindex="0"
							>
								<div class="tile-header-bar">
									<span class="badge-tag {jobsByStagedId[item.id]?.status === 'error' ? 'err' : 'ingest'}">
										{#if jobsByStagedId[item.id]?.status === 'error'}Failed{:else}Ingesting{/if}
									</span>
								</div>
								<div class="tile-art doc-art">
									<Icon name="file" size={tileIconSizes.staged} />
								</div>
								<span class="tile-label">{item.filename ?? item.source_url ?? 'Pasted text'}</span>
								{#if jobsByStagedId[item.id]?.status === 'error'}
									<span class="tile-sub job-error">{jobsByStagedId[item.id]?.error_message || 'Processing failed'}</span>
									<div class="staged-tile-footer">
										<button class="staged-pill-btn" onclick={(e) => { e.stopPropagation(); ingestOne(item.id); }}>Retry</button>
										<button class="staged-pill-btn danger" onclick={(e) => { e.stopPropagation(); removeStagedFile(item.id); }}>Remove</button>
									</div>
								{:else}
									<div class="job-progress tiny">
										<div class="track"><div class="fill" style="width: {jobProgressPercent(jobsByStagedId[item.id] ?? { step: 'queued' })}%"></div></div>
										<span class="job-pct">{jobProgressPercent(jobsByStagedId[item.id] ?? { step: 'queued' })}%</span>
									</div>
									<div class="staged-tile-footer">
										<button class="staged-pill-btn danger" onclick={(e) => { e.stopPropagation(); stopIngesting(item.id); }} title="Stop ingesting">Stop</button>
										<button class="staged-pill-btn danger" onclick={(e) => { e.stopPropagation(); removeStagedFile(item.id); }} title="Stop ingesting and remove file">Remove</button>
									</div>
								{/if}
							</div>
						{/each}
					{/if}
					{#each filtered as s (s.id)}
						<button
							class="icon-tile doc-tile"
							class:on={selectedDocId === s.id}
							class:selected={librarySelected.has(s.id)}
							data-doc-id={s.id}
							oncontextmenu={(e) => onDocContextMenu(e, s)}
							draggable="true"
							ondragstart={() => (draggedId = s.id)}
							ondragend={() => (draggedId = null)}
							onclick={(e) => onDocClick(e, s)}
							ondblclick={() => window.open(`/admin/${s.id}`, '_blank')}
						>
							<div class="tile-header-bar">
								<span class="file-ext-tag">{s.filename?.split('.').pop()?.toUpperCase() || s.doc_type || 'DOC'}</span>
								<div class="tile-badges">
									{#if s.is_private}<span class="tile-badge lock" title="Private"><Icon name="lock" size={tileBadgeIconSize} /></span>{/if}
									{#if needsFinalization.has(s.id)}<span class="tile-badge bell" title="Needs placement review"><Icon name="bell" size={tileBadgeIconSize} /></span>{/if}
									<input
										type="checkbox"
										class="tile-select-check"
										class:visible={librarySelected.size > 0 || librarySelected.has(s.id)}
										checked={librarySelected.has(s.id)}
										onclick={(e) => { e.stopPropagation(); toggleLibrarySelected(s.id); }}
										aria-label="Select {s.title}"
									/>
								</div>
							</div>
							<div class="tile-art doc-art">
								<Icon name={fileIcon(s)} size={tileIconSizes.doc} />
							</div>
							<span class="tile-label">{s.title}</span>
							<span class="tile-footer-hint">Double-click to open</span>
						</button>
					{:else}
						<div class="list-empty">
							{#if !data.sources.length}
								<EmptyState icon="book" title="Your library is empty" body='Upload a document, paste text, or scrape a URL to start teaching Functional Health Collab.'>
									{#snippet action()}<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>{/snippet}
								</EmptyState>
							{:else if searching}
								<EmptyState icon="search" title="Nothing matches that search" body="Try a different term, or clear the search.">
									{#snippet action()}<Button variant="ghost" onclick={() => { q = ''; }}>Clear search</Button>{/snippet}
								</EmptyState>
							{:else if (mainTab === 'tags' ? !visibleSubtags.length : !visibleSubfolders.length)}
								<EmptyState icon={mainTab === 'tags' ? 'tag' : 'folder'} title={mainTab === 'tags' ? 'This category is empty' : 'This folder is empty'} body={mainTab === 'tags' ? 'Drag documents here to tag them, or browse to another category.' : 'Upload a document here, or browse to another folder.'}>
									{#snippet action()}<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>{/snippet}
								</EmptyState>
							{/if}
						</div>
					{/each}
				</div>
			{:else if viewMode === 'list'}
				<!-- Finder's List View: a real table — Name, Date, Type,
				     Grade columns, not a card. -->
				<table class="finder-table">
					<thead>
						<tr><th></th><th>Name</th><th>Type</th><th>Grade</th><th>Date</th></tr>
					</thead>
					<tbody>
						{#if !searching}
							{#if mainTab === 'library'}
								{#each visibleSubfolders as node (node.path)}
									<tr
										class="folder-tr"
										class:on={selectedFolderPath === node.path}
										class:selected={selectedFolderPaths.has(node.path)}
										data-folder-path={node.path}
										draggable="true"
										ondragstart={() => (draggedFolderPath = node.path)}
										ondragend={() => { draggedFolderPath = null; dragOverPath = null; }}
										ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = node.path; }}
										ondragleave={() => (dragOverPath = null)}
										ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnFolder(node.path, e); }}
										onclick={(e) => onFolderClick(e, node)}
										ondblclick={() => { currentPath = node.path; clearAllSelections(); }}
										oncontextmenu={(e) => onFolderContextMenu(e, node)}
									>
										<td>
											<input
												type="checkbox"
												checked={selectedFolderPaths.has(node.path)}
												onclick={(e) => e.stopPropagation()}
												onchange={() => toggleFolderSelected(node.path)}
												aria-label="Select folder {node.name}"
											/>
										</td>
										<td><Icon name="folder" size={16} /> {node.name}</td>
										<td class="hint">Folder</td>
										<td class="hint">—</td>
										<td class="hint">{node.count} item{node.count === 1 ? '' : 's'}</td>
									</tr>
								{/each}
							{:else}
								{#each visibleSubtags as node (node.path)}
									<tr
										class="folder-tr tag-tr"
										class:on={selectedTagPath === node.path}
										class:selected={selectedTagPaths.has(node.path)}
										data-tag-path={node.path}
										ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = node.path; }}
										ondragleave={() => (dragOverPath = null)}
										ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnTag(node.path, e); }}
										onclick={(e) => onTagClick(e, node)}
										ondblclick={() => { currentTag = node.path; clearAllSelections(); }}
										oncontextmenu={(e) => onTagContextMenu(e, node)}
									>
										<td>
											<input
												type="checkbox"
												checked={selectedTagPaths.has(node.path)}
												onclick={(e) => e.stopPropagation()}
												onchange={() => toggleTagSelected(node.path)}
												aria-label="Select category {node.name}"
											/>
										</td>
										<td><Icon name="tag" size={16} /> {node.name}</td>
										<td class="hint">Category</td>
										<td class="hint">—</td>
										<td class="hint">{node.count} item{node.count === 1 ? '' : 's'}</td>
									</tr>
								{/each}
							{/if}
						{/if}
						{#if !searching}
							{#each (data.staged ?? []).filter(isStagedVisible) as item (item.id)}
								<tr
									class="doc-tr staged-tr"
									class:error={jobsByStagedId[item.id]?.status === 'error'}
									oncontextmenu={(e) => onStagedContextMenu(e, item)}
								>
									<td><Icon name="file" size={16} /></td>
									<td>
										<div class="staged-row-title">
											<span class="staged-name">{item.filename ?? item.source_url ?? 'Pasted text'}</span>
											<span class="badge-tag {jobsByStagedId[item.id]?.status === 'error' ? 'err' : 'ingest'}">
												{jobsByStagedId[item.id]?.status === 'error' ? 'Failed' : 'Ingesting'}
											</span>
										</div>
									</td>
									<td class="hint">
										{#if jobsByStagedId[item.id]?.status === 'error'}
											Failed
										{:else}
											{jobProgressPercent(jobsByStagedId[item.id] ?? { step: 'queued' })}% ({jobLabel(jobsByStagedId[item.id] ?? { step: 'queued' })})
										{/if}
									</td>
									<td class="hint">—</td>
									<td>
										<div class="staged-row-actions">
											{#if jobsByStagedId[item.id]?.status === 'error'}
												<button class="staged-table-btn" onclick={() => ingestOne(item.id)}>Retry</button>
												<button class="staged-table-btn danger" onclick={() => removeStagedFile(item.id)}>Remove</button>
											{:else}
												<button class="staged-table-btn danger" onclick={() => stopIngesting(item.id)}>Stop</button>
												<button class="staged-table-btn danger" onclick={() => removeStagedFile(item.id)}>Remove</button>
											{/if}
										</div>
									</td>
								</tr>
							{/each}
						{/if}
						{#each filtered as s (s.id)}
							<tr
								class="doc-tr"
								class:on={selectedDocId === s.id}
								class:selected={librarySelected.has(s.id)}
								data-doc-id={s.id}
								oncontextmenu={(e) => onDocContextMenu(e, s)}
								draggable="true"
								ondragstart={() => (draggedId = s.id)}
								ondragend={() => (draggedId = null)}
								onclick={(e) => onDocClick(e, s)}
								ondblclick={() => window.open(`/admin/${s.id}`, '_blank')}
							>
								<td>
									<input
										type="checkbox"
										checked={librarySelected.has(s.id)}
										onclick={(e) => e.stopPropagation()}
										onchange={() => toggleLibrarySelected(s.id)}
										aria-label="Select {s.title}"
									/>
								</td>
								<td>
									<Icon name={fileIcon(s)} size={14} />
									{s.title}
									{#if needsFinalization.has(s.id)}<Icon name="bell" size={11} />{/if}
									{#if s.is_private}<Icon name="lock" size={11} />{/if}
								</td>
								<td class="hint">{s.doc_type || '—'}</td>
								<td class="hint">{s.grade}</td>
								<td class="hint">{(s.created_at ?? '').slice(0, 10)}</td>
							</tr>
						{:else}
							<tr><td colspan="5">
								<div class="list-empty">
									{#if !data.sources.length}
										<EmptyState icon="book" title="Your library is empty" body='Upload a document, paste text, or scrape a URL to start teaching Functional Health Collab.'>
											{#snippet action()}<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>{/snippet}
										</EmptyState>
									{:else if searching}
										<EmptyState icon="search" title="Nothing matches that search" body="Try a different term, or clear the search.">
											{#snippet action()}<Button variant="ghost" onclick={() => { q = ''; }}>Clear search</Button>{/snippet}
										</EmptyState>
									{:else if (mainTab === 'tags' ? !visibleSubtags.length : !visibleSubfolders.length)}
										<EmptyState icon={mainTab === 'tags' ? 'tag' : 'folder'} title={mainTab === 'tags' ? 'This category is empty' : 'This folder is empty'} body={mainTab === 'tags' ? 'Drag documents here to tag them, or browse to another category.' : 'Upload a document here, or browse to another folder.'}>
											{#snippet action()}<Button onclick={() => (ingestOpen = true)}>+ Add resources</Button>{/snippet}
										</EmptyState>
									{/if}
								</div>
							</td></tr>
						{/each}
					</tbody>
				</table>
			{:else}
				<!-- Finder's Column View: one column per hierarchy level,
				     each showing its own siblings so a different branch is
				     always one click away without losing where you are. -->
				<div class="column-view">
					{#if mainTab === 'tags'}
						{#each tagColumns as col, i (col.path)}
							<div class="col-pane">
								{#each col.nodes as node (node.path)}
									<button
										class="col-row tag-col-row"
										class:active={currentTag === node.path || currentTag.startsWith(`${node.path}/`)}
										class:selected={selectedTagPaths.has(node.path)}
										class:drag-target={dragOverPath === node.path}
										data-tag-path={node.path}
										ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = node.path; }}
										ondragleave={() => (dragOverPath = null)}
										ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnTag(node.path, e); }}
										onclick={(e) => {
											if (e.shiftKey || e.metaKey || e.ctrlKey) {
												onTagClick(e, node);
											} else {
												currentTag = node.path;
												clearAllSelections();
											}
										}}
										oncontextmenu={(e) => onTagContextMenu(e, node)}
									>
										<Icon name="tag" size={14} /> {node.name}
										<span class="row-sub">{node.count}</span>
										{#if node.children.length}<Icon name="chevron" size={11} />{/if}
									</button>
								{/each}
								{#if i === tagColumns.length - 1}
									{#each filtered as s (s.id)}
										<button
											class="col-row doc"
											class:active={selectedDocId === s.id}
											class:selected={librarySelected.has(s.id)}
											data-doc-id={s.id}
											oncontextmenu={(e) => onDocContextMenu(e, s)}
											draggable="true"
											ondragstart={() => (draggedId = s.id)}
											ondragend={() => (draggedId = null)}
											onclick={(e) => onDocClick(e, s)}
											ondblclick={() => window.open(`/admin/${s.id}`, '_blank')}
										>
											<Icon name={fileIcon(s)} size={14} /> {s.title}
										</button>
									{/each}
									{#if !col.nodes.length && !filtered.length}
										<p class="hint col-empty">Empty.</p>
									{/if}
								{/if}
							</div>
						{/each}
					{:else}
						{#each folderColumns as col, i (col.path)}
							<div class="col-pane">
								{#each col.nodes as node (node.path)}
									<button
										class="col-row folder-col-row"
										class:active={currentPath === node.path || currentPath.startsWith(`${node.path}/`)}
										class:selected={selectedFolderPaths.has(node.path)}
										class:drag-target={dragOverPath === node.path}
										data-folder-path={node.path}
										draggable="true"
										ondragstart={() => (draggedFolderPath = node.path)}
										ondragend={() => { draggedFolderPath = null; dragOverPath = null; }}
										ondragover={(e) => { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'; dragOverPath = node.path; }}
										ondragleave={() => (dragOverPath = null)}
										ondrop={(e) => { e.preventDefault(); e.stopPropagation(); handleDropOnFolder(node.path, e); }}
										onclick={(e) => {
											if (e.shiftKey || e.metaKey || e.ctrlKey) {
												onFolderClick(e, node);
											} else {
												currentPath = node.path;
												clearAllSelections();
											}
										}}
										oncontextmenu={(e) => onFolderContextMenu(e, node)}
									>
										<Icon name="folder" size={14} /> {node.name}
										<span class="row-sub">{node.count}</span>
										{#if node.children.length}<Icon name="chevron" size={11} />{/if}
									</button>
								{/each}
								{#if i === folderColumns.length - 1}
									{#each filtered as s (s.id)}
										<button
											class="col-row doc"
											class:active={selectedDocId === s.id}
											class:selected={librarySelected.has(s.id)}
											data-doc-id={s.id}
											oncontextmenu={(e) => onDocContextMenu(e, s)}
											draggable="true"
											ondragstart={() => (draggedId = s.id)}
											ondragend={() => (draggedId = null)}
											onclick={(e) => onDocClick(e, s)}
											ondblclick={() => window.open(`/admin/${s.id}`, '_blank')}
										>
											<Icon name={fileIcon(s)} size={14} /> {s.title}
										</button>
									{/each}
									{#if !col.nodes.length && !filtered.length}
										<p class="hint col-empty">Empty.</p>
									{/if}
								{/if}
							</div>
						{/each}
					{/if}
				</div>
			{/if}
		</div>

		{#if selectedDoc}
			<!-- The Inspector: Finder's Get Info panel, not a permanently-
			     reserved half-width pane — it only takes space once
			     something is actually selected, and can be dismissed. -->
			{@const s = selectedDoc}
			<aside class="inspector">
				<div class="inspector-head">
					<h2>{s.title}</h2>
					<button class="icon-btn" onclick={closeInspector} title="Close" aria-label="Close inspector"><Icon name="x" size={15} /></button>
				</div>
				<p class="hint">{s.author ? `by ${s.author}` : 'No author on record'}{s.uploaded_by ? ` · uploaded by ${s.uploaded_by}` : ''}</p>
				{#if searching && contentSnippets[s.id]}
					<!-- Why this showed up under a content search — the
					     endpoint's own highlighted excerpt (HTML-escaped
					     server-side, only <mark> is real markup). -->
					<p class="match-snippet">{@html contentSnippets[s.id]}</p>
				{/if}
				<div class="inspector-actions">
					<a class="icon-btn" href="/admin/{s.id}" title="Open full detail" aria-label="Open full detail"><Icon name="external-link" size={16} /></a>
					<Menu label="More actions for {s.title}">
						{#snippet items()}
							<button onclick={() => askMove(s)}><Icon name="folder" size={15} /> Move to folder…</button>
							{#if s.is_private}<button onclick={() => askAccess(s)}><Icon name="users" size={15} /> Edit access…</button>{/if}
							<button onclick={() => askAssignUploader(s)}><Icon name="user-card" size={15} /> {s.uploaded_by ? 'Reassign uploader…' : 'Assign uploader…'}</button>
							<button class="danger" onclick={() => askDelete(s)}><Icon name="trash" size={15} /> Remove from library</button>
						{/snippet}
					</Menu>
				</div>

				{#if needsFinalization.has(s.id)}
					<button class="finalize-notice" onclick={() => openPlacementForDoc(s)}>
						<Icon name="bell" size={14} /> This was just filed automatically — review where it landed
					</button>
				{/if}

				<div class="detail-fields">
					<label class="field">
						<span>Type</span>
						<select value={s.doc_type ?? ''} onchange={(e) => setDocType(s, (e.target as HTMLSelectElement).value)}>
							<option value="">(unset)</option>
							{#each DOC_TYPES as t (t)}<option value={t}>{t}</option>{/each}
						</select>
					</label>
					<label class="field">
						<span>Grade</span>
						<input type="number" min="1" max="10" value={s.grade} onchange={(e) => regrade(s, Number((e.target as HTMLInputElement).value))} />
					</label>
					<label class="field">
						<span>Folder</span>
						<input type="text" placeholder="(root)" value={s.folder_path ?? ''} onblur={(e) => setFolder(s, (e.target as HTMLInputElement).value)} />
					</label>
					<label class="field">
						<span>Visibility</span>
						<button class="visibility-toggle" class:is-private={s.is_private} onclick={() => setPrivate(s, !s.is_private)}>
							<Icon name={s.is_private ? 'lock' : 'unlock'} size={14} /> {s.is_private ? 'Private' : 'Public'}
						</button>
					</label>
				</div>

				<div class="field">
					<span>Tags</span>
					<div class="tags">
						{#each s.topics ?? [] as tag (tag)}
							<button class="tag" onclick={() => removeTag(s, tag)} title="Remove tag">{tag} <span aria-hidden="true">&times;</span></button>
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
				</div>
			</aside>
		{/if}
	</div>
</div>

<Dialog bind:open={maintenanceOpen} title={maintenanceKind === 'relink' ? 'Relink unlinked sources' : 'Consolidate entities'}>
	{#if maintenanceRunning && maintenanceProgress}
		<div class="dialog-maintenance-running">
			<div class="dialog-m-header">
				<span class="m-icon spin">
					<Icon name={maintenanceProgress.kind === 'relink' ? 'refresh' : 'sparkles'} size={18} />
				</span>
				<div class="dialog-m-titles">
					<strong>{maintenanceProgress.kind === 'relink' ? 'Building knowledge connections…' : 'Merging duplicate entities…'}</strong>
					<p class="dialog-m-detail">{maintenanceProgress.detail || 'Processing…'}</p>
				</div>
			</div>
			<div class="dialog-m-progress">
				<div class="m-track large" role="progressbar" aria-valuenow={maintenanceProgress.percentage} aria-valuemin={0} aria-valuemax={100}>
					<div class="m-fill" style="width: {maintenanceProgress.percentage}%"></div>
				</div>
				<div class="dialog-m-pct-row">
					<span>{maintenanceProgress.percentage}% complete</span>
					{#if maintenanceProgress.total > 1}
						<span>{Math.min(maintenanceProgress.total, Math.floor(maintenanceProgress.current))} of {maintenanceProgress.total}</span>
					{/if}
				</div>
			</div>
			<p class="dialog-m-hint">You can close this window at any time — progress will remain active in the top bar.</p>
		</div>
	{:else}
		<p>
			{maintenanceKind === 'relink'
				? 'Build the knowledge graph for any ingested sources that have none yet. This can take a while for a large backlog.'
				: 'Let the model suggest entity merges, then rewrite the graph to match. Requires Neo4j APOC.'}
		</p>
	{/if}
	{#snippet footer()}
		{#if maintenanceRunning}
			<Button variant="ghost" onclick={stopMaintenanceTask} loading={maintenanceStopping}>Stop</Button>
			<Button onclick={() => (maintenanceOpen = false)}>Run in background</Button>
		{:else}
			<Button variant="ghost" onclick={() => (maintenanceOpen = false)}>Cancel</Button>
			<Button onclick={runMaintenance} loading={maintenanceRunning}>Run</Button>
		{/if}
	{/snippet}
</Dialog>

{#if ctxMenu}
	{@const menu = ctxMenu}
	<ContextMenu x={menu.x} y={menu.y} onClose={closeContextMenu}>
		{#snippet items()}
			{#if menu.kind === 'doc'}
				{@const s = menu.target}
				<button onclick={() => { selectedDocId = s.id; closeContextMenu(); }}><Icon name="eye" size={15} /> Open</button>
				{#if mainTab === 'tags' && currentTag && currentTag !== '__untagged__'}
					<button onclick={() => { removeTag(s, currentTag); closeContextMenu(); }}><Icon name="tag" size={15} /> Remove from "{currentTag}"</button>
				{/if}
				<button onclick={() => askMove(s)}><Icon name="folder" size={15} /> Move to folder…</button>
				{#if s.is_private}<button onclick={() => askAccess(s)}><Icon name="users" size={15} /> Edit access…</button>{/if}
				<button onclick={() => askAssignUploader(s)}><Icon name="user-card" size={15} /> {s.uploaded_by ? 'Reassign uploader…' : 'Assign uploader…'}</button>
				<button class="danger" onclick={() => askDelete(s)}><Icon name="trash" size={15} /> Remove from library</button>
			{:else if menu.kind === 'folder'}
				{@const node = menu.target}
				<button onclick={() => { currentPath = node.path; selectedFolderPath = null; closeContextMenu(); }}><Icon name="folder" size={15} /> Open</button>
				<button onclick={() => askRenameFolder(node.path)}><Icon name="edit" size={15} /> Rename…</button>
				<button onclick={() => setFolderPrivate(node.path, true)}><Icon name="lock" size={15} /> Privatize</button>
				<button onclick={() => setFolderPrivate(node.path, false)}><Icon name="unlock" size={15} /> Make public</button>
				<button class="danger" onclick={() => askDeleteFolder(node.path, node.count)}><Icon name="trash" size={15} /> Delete folder</button>
			{:else if menu.kind === 'tag'}
				{@const node = menu.target}
				<button onclick={() => { currentTag = node.path; selectedTagPath = null; closeContextMenu(); }}><Icon name="tag" size={15} /> Open category</button>
				{#if node.path !== '__untagged__'}
					<button onclick={() => { askRenameTag(node.path); closeContextMenu(); }}><Icon name="edit" size={15} /> Rename category…</button>
					<button class="danger" onclick={() => { askDeleteTag(node.path, node.count); closeContextMenu(); }}><Icon name="trash" size={15} /> Remove category</button>
				{/if}
			{:else if menu.kind === 'staged'}
				{@const item = menu.target}
				{@const job = jobsByStagedId[item.id]}
				{@const isRunning = jobActive(job)}
				{#if isRunning}
					<button onclick={() => { stopIngesting(item.id); closeContextMenu(); }}>
						<Icon name="x" size={15} /> Stop ingesting
					</button>
					<button class="danger" onclick={() => { removeStagedFile(item.id); closeContextMenu(); }}>
						<Icon name="trash" size={15} /> Stop ingesting and remove file
					</button>
				{:else}
					<button onclick={() => { ingestOne(item.id); closeContextMenu(); }}>
						<Icon name="sparkles" size={15} /> Retry ingestion
					</button>
					<button class="danger" onclick={() => { removeStagedFile(item.id); closeContextMenu(); }}>
						<Icon name="trash" size={15} /> Remove file
					</button>
				{/if}
			{:else if menu.kind === 'bulk' || menu.kind === 'bulk-doc'}
				<div class="ctx-header">
					<Icon name="check" size={13} />
					<span>
						{totalSelectedCount} item{totalSelectedCount === 1 ? '' : 's'} selected
						{#if selectedFolderPaths.size > 0 || selectedTagPaths.size > 0}
							<small class="ctx-sub">
								({selectedFolderPaths.size > 0 ? `${selectedFolderPaths.size} folder${selectedFolderPaths.size > 1 ? 's' : ''}` : ''}
								{selectedFolderPaths.size > 0 && librarySelected.size > 0 ? ', ' : ''}
								{librarySelected.size > 0 ? `${librarySelected.size} file${librarySelected.size > 1 ? 's' : ''}` : ''}
								{(selectedFolderPaths.size > 0 || librarySelected.size > 0) && selectedTagPaths.size > 0 ? ', ' : ''}
								{selectedTagPaths.size > 0 ? `${selectedTagPaths.size} categor${selectedTagPaths.size > 1 ? 'ies' : 'y'}` : ''})
							</small>
						{/if}
					</span>
				</div>
				{#if selectedFolderPaths.size > 0 || librarySelected.size > 0}
					<button onclick={() => { askBulkMove(); closeContextMenu(); }}>
						<Icon name="folder" size={15} /> Move {selectedFolderPaths.size + librarySelected.size} items to folder…
					</button>
				{/if}
				{#if librarySelected.size > 0}
					<button onclick={() => { askBulkTag(); closeContextMenu(); }}>
						<Icon name="tag" size={15} /> Assign category to {librarySelected.size} items…
					</button>
				{/if}
				{#if mainTab === 'tags' && currentTag && currentTag !== '__untagged__' && librarySelected.size > 0}
					<button onclick={() => { bulkRemoveTag(currentTag); closeContextMenu(); }}>
						<Icon name="tag" size={15} /> Remove from "{currentTag}"
					</button>
				{/if}
				{#if selectedFolderPaths.size > 0 || librarySelected.size > 0}
					<button onclick={() => { setPrivateBulk(true); closeContextMenu(); }}>
						<Icon name="lock" size={15} /> Make private ({selectedFolderPaths.size + librarySelected.size})
					</button>
					<button onclick={() => { setPrivateBulk(false); closeContextMenu(); }}>
						<Icon name="unlock" size={15} /> Make public ({selectedFolderPaths.size + librarySelected.size})
					</button>
				{/if}
				<button class="danger" onclick={() => { askDeleteBulk(); closeContextMenu(); }}>
					<Icon name="trash" size={15} /> Remove {totalSelectedCount} items
				</button>
				<button onclick={() => { clearAllSelections(); closeContextMenu(); }}>
					<Icon name="x" size={15} /> Clear selection
				</button>
			{:else}
				<button onclick={() => (ingestOpen = true)}><Icon name="plus" size={15} /> Add resources</button>
				{#if mainTab === 'tags'}
					<button onclick={() => { newCategoryName = ''; newCategoryOpen = true; closeContextMenu(); }}><Icon name="tag" size={15} /> New category</button>
				{:else}
					<button onclick={() => { newFolderName = ''; newFolderOpen = true; closeContextMenu(); }}><Icon name="folder" size={15} /> New folder</button>
				{/if}
				{#if viewMode === 'icons'}
					<div class="ctx-divider"></div>
					<div class="ctx-header">
						<span>Icon & Folder Size</span>
					</div>
					<button class:menu-active={iconSize === 'small'} onclick={() => { iconSize = 'small'; closeContextMenu(); }}>
						{#if iconSize === 'small'}<Icon name="check" size={13} />{:else}<span class="menu-check-spacer"></span>{/if}
						<Icon name="size-small" size={14} /> Small
					</button>
					<button class:menu-active={iconSize === 'medium'} onclick={() => { iconSize = 'medium'; closeContextMenu(); }}>
						{#if iconSize === 'medium'}<Icon name="check" size={13} />{:else}<span class="menu-check-spacer"></span>{/if}
						<Icon name="size-medium" size={14} /> Medium
					</button>
					<button class:menu-active={iconSize === 'large'} onclick={() => { iconSize = 'large'; closeContextMenu(); }}>
						{#if iconSize === 'large'}<Icon name="check" size={13} />{:else}<span class="menu-check-spacer"></span>{/if}
						<Icon name="size-large" size={14} /> Large (current)
					</button>
				{/if}
			{/if}
		{/snippet}
	</ContextMenu>
{/if}

<Dialog bind:open={ingestOpen} title="Add resources" wide>
	<Tabs bind:active={ingestTab} tabs={[{ id: 'upload', label: 'Upload a document' }, { id: 'text', label: 'Paste text' }, { id: 'url', label: 'Enter URL' }]} />

	<div class="ingest-panel">
		{#if ingestTab === 'upload'}
			<input id="file" type="file" bind:this={fileInput} onchange={onFileInputChange} multiple hidden />
			<!-- svelte-ignore a11y_no_noninteractive_element_to_interactive_role -->
			<div
				class="dropzone"
				class:dragover={dragOver}
				class:has-file={selectedFiles.length > 0}
				role="button"
				tabindex="0"
				ondragover={(e) => { e.preventDefault(); dragOver = true; }}
				ondragleave={() => (dragOver = false)}
				ondrop={onDrop}
				onclick={() => fileInput?.click()}
				onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput?.click(); } }}
			>
				{#if selectedFiles.length === 0}
					<Icon name="upload" size={30} />
					<p class="dz-title">Drag files here, or click to browse</p>
					<p class="hint">Select multiple documents at once (PDF, TXT, MD, DOCX, CSV). Up to 200 MB each.</p>
				{:else if selectedFiles.length === 1}
					{@const file = selectedFiles[0]}
					{#if previewUrls[file.name] && file.type === 'application/pdf'}
						<embed src="{previewUrls[file.name]}#toolbar=0&navpanes=0&scrollbar=0" type="application/pdf" class="pdf-preview" aria-label="{file.name} preview" />
						<p class="dz-filename">{file.name}</p>
					{:else}
						<Icon name="file" size={32} />
						<p class="dz-title">{file.name}</p>
						<p class="hint">{Math.round(file.size / 1024)} KB</p>
					{/if}
				{:else}
					<div class="multi-file-summary">
						<Icon name="folder" size={22} />
						<span class="multi-count">{selectedFiles.length} files selected</span>
						<span class="multi-size">({(selectedFiles.reduce((acc, f) => acc + f.size, 0) / (1024 * 1024)).toFixed(1)} MB total)</span>
					</div>
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div class="multi-file-list" onclick={(e) => e.stopPropagation()}>
						{#each selectedFiles as file, idx (file.name + idx)}
							<div class="multi-file-item">
								<Icon name="file" size={13} />
								<span class="multi-name" title={file.name}>{file.name}</span>
								<span class="multi-kb">{Math.round(file.size / 1024)} KB</span>
								<button type="button" class="multi-del" onclick={() => removeFile(idx)} aria-label="Remove {file.name}">×</button>
							</div>
						{/each}
					</div>
					<p class="multi-add-more">+ Click or drop to add more files</p>
				{/if}
			</div>
			{#if currentPath}
				<div class="target-folder-notice">
					<Icon name="folder" size={13} />
					<span>Destination folder: <strong>{currentPath}</strong></span>
				</div>
			{/if}
			{#if mainTab === 'tags' && currentTag && currentTag !== '__untagged__'}
				<div class="target-folder-notice">
					<Icon name="tag" size={13} />
					<span>Destination category: <strong>{currentTag}</strong></span>
				</div>
			{/if}
			{#if multiUploadProgress}
				<div class="multi-progress">
					<div class="multi-progress-head">
						<span>Uploading {multiUploadProgress.current} of {multiUploadProgress.total}</span>
						<span class="multi-curr-file">{multiUploadProgress.filename}</span>
					</div>
					<div class="bar-track">
						<div class="bar-fill" style="width: {(multiUploadProgress.current / multiUploadProgress.total) * 100}%"></div>
					</div>
				</div>
			{:else if stageProgress}
				<div class="upload-progress">
					<div class="bar" style="width: {Math.round((stageProgress.sent / stageProgress.total) * 100)}%"></div>
					<span class="hint">{Math.round(stageProgress.sent / 1024 / 1024)} / {Math.round(stageProgress.total / 1024 / 1024)} MB</span>
				</div>
			{/if}
			<div class="dz-actions">
				{#if selectedFiles.length > 0}
					<Button variant="ghost" onclick={clearSelectedFiles}>Clear all ({selectedFiles.length})</Button>
				{/if}
				<Button onclick={stageFiles} loading={staging} disabled={selectedFiles.length === 0}>
					{#if selectedFiles.length > 1}
						Upload {selectedFiles.length} files and queue for ingestion
					{:else}
						Upload and queue for ingestion
					{/if}
				</Button>
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
					<p class="hint"><Spinner size={13} /> Fetching and extracting…</p>
				{/if}
				<Button type="submit" loading={scraping}>Scrape and queue for ingestion</Button>
			</form>
		{/if}
	</div>
</Dialog>

<Dialog bind:open={confirmingDelete} title={deletingBulk ? `Remove ${totalSelectedCount} items` : "Remove source"}>
	{#if deletingBulk}
		<p>
			Remove
			{#if selectedFolderPaths.size > 0}
				<strong>{selectedFolderPaths.size} folder{selectedFolderPaths.size === 1 ? '' : 's'}</strong>
				{librarySelected.size > 0 || selectedTagPaths.size > 0 ? 'and ' : ''}
			{/if}
			{#if librarySelected.size > 0}
				<strong>{librarySelected.size} source{librarySelected.size === 1 ? '' : 's'}</strong>
				{selectedTagPaths.size > 0 ? 'and ' : ''}
			{/if}
			{#if selectedTagPaths.size > 0}
				<strong>{selectedTagPaths.size} categor{selectedTagPaths.size === 1 ? 'y' : 'ies'}</strong>
			{/if}
			? Answers will stop citing deleted documents. This cannot be undone.
		</p>
	{:else if deleting}
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

<Dialog bind:open={newCategoryOpen} title="New category">
	<form onsubmit={(e) => { e.preventDefault(); createCategory(newCategoryName); }} id="nc-form">
		<p class="hint">Inside "{currentTag && currentTag !== '__untagged__' ? currentTag : 'Root categories'}".</p>
		<TextField label="Category name" bind:value={newCategoryName} placeholder="e.g. cardiology" />
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (newCategoryOpen = false)}>Cancel</Button>
		<Button onclick={() => createCategory(newCategoryName)}>Create</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={renameTagOpen} title="Rename category">
	<form onsubmit={(e) => { e.preventDefault(); confirmRenameTag(); }} id="rt-form">
		<TextField label="Current name" bind:value={renameTagOld} disabled />
		<TextField label="New category name" bind:value={renameTagNew} placeholder="e.g. endocrinology" />
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (renameTagOpen = false)}>Cancel</Button>
		<Button onclick={confirmRenameTag}>Rename</Button>
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
	{#if movingBulk}
		<form onsubmit={confirmMove} id="mv-bulk-form">
			<p class="hint">
				Moving {selectedFolderPaths.size + librarySelected.size} selected item{selectedFolderPaths.size + librarySelected.size === 1 ? '' : 's'}
				{#if selectedFolderPaths.size > 0}
					({selectedFolderPaths.size} folder{selectedFolderPaths.size === 1 ? '' : 's'}{librarySelected.size > 0 ? `, ${librarySelected.size} document${librarySelected.size === 1 ? '' : 's'}` : ''})
				{/if}.
			</p>
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
	{:else if movingSource}
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
		<Button onclick={confirmMove}>{movingBulk ? `Move ${selectedFolderPaths.size + librarySelected.size} items` : 'Move'}</Button>
	{/snippet}
</Dialog>

<Dialog bind:open={bulkTagOpen} title="Assign category to {librarySelected.size} items">
	<form onsubmit={confirmBulkTag} id="bulk-tag-form">
		<p class="hint">Assign a tag or category (e.g. <code>cardiology</code> or <code>cardiology/arrhythmia</code>) to {librarySelected.size} selected documents.</p>
		<TextField label="Category tag" bind:value={bulkTagInput} placeholder="e.g. pharmacology" list="bulk-known-tags" />
		<datalist id="bulk-known-tags">
			{#each allKnownTags as t (t)}
				<option value={t}></option>
			{/each}
		</datalist>
		{#if allKnownTags.length}
			<p class="hint">Existing categories:</p>
			<div class="move-suggestions">
				{#each allKnownTags.slice(0, 15) as t (t)}
					<button type="button" class="fchip" onclick={() => (bulkTagInput = t)}>{t}</button>
				{/each}
			</div>
		{/if}
	</form>
	{#snippet footer()}
		<Button variant="ghost" onclick={() => (bulkTagOpen = false)}>Cancel</Button>
		<Button onclick={confirmBulkTag}>Assign category</Button>
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

<!-- Multi-file placement confirmation dialog (specs/v15/05, v15/12) -->
<Dialog bind:open={placementDialogOpen} title="Confirm File Placements & Tags" wide>
	{#if pendingPlacements.length === 0}
		<div class="empty-placements">
			<Icon name="check" size={24} />
			<p>All ingested files have been placed in their destination folders and tagged.</p>
		</div>
	{:else}
		<div class="placements-header-hint">
			<p>
				<strong>{pendingPlacements.length} file{pendingPlacements.length === 1 ? '' : 's'}</strong>
				finished ingestion. Review destination folder and tags (AI suggested):
			</p>
		</div>

		<div class="placement-list">
			{#each pendingPlacements as item (item.documentId)}
				<div class="placement-card">
					<div class="placement-card-header">
						<span class="placement-file-icon"><Icon name="file" size={16} /></span>
						<div class="placement-file-title-wrap">
							<span class="placement-file-title" title={item.title}>{item.title}</span>
							<div class="placement-meta-row">
								{#if item.docType}<span class="placement-chip type">{item.docType}</span>{/if}
								{#if item.suggestedFolder}
									<span class="placement-chip suggested" title="Suggested based on intake context">
										<Icon name="folder" size={11} />
										Suggested: <strong>/{item.suggestedFolder}</strong>
									</span>
								{:else}
									<span class="placement-chip suggested root" title="Suggested root destination">
										<Icon name="folder" size={11} />
										Suggested: <strong>Library root (/)</strong>
									</span>
								{/if}
								{#if item.suggestedTags && item.suggestedTags.length > 0}
									<span class="placement-chip ai-tags-badge" title="{item.suggestedTags.length} AI suggested tag{item.suggestedTags.length === 1 ? '' : 's'}">
										<Icon name="sparkles" size={11} />
										{item.suggestedTags.length} AI tag{item.suggestedTags.length === 1 ? '' : 's'}
									</span>
								{/if}
							</div>
						</div>
					</div>

					<div class="placement-card-body">
						{#if !item.isCreatingNewFolder}
							<!-- No text input: dropdown with existing folders and option to create new -->
							<div class="placement-folder-row">
								<label class="placement-field-label" for="placement-folder-{item.documentId}">
									Destination:
								</label>
								<div class="placement-select-group">
									<select
										id="placement-folder-{item.documentId}"
										class="placement-dropdown"
										bind:value={item.selectedFolder}
										onchange={(e) => {
											if ((e.target as HTMLSelectElement).value === '__NEW__') {
												item.isCreatingNewFolder = true;
												item.newFolderName = '';
											}
										}}
									>
										<option value="">/ (Library root) {!item.suggestedFolder ? '★ Suggested' : ''}</option>
										{#if item.suggestedFolder && !folderPaths.includes(item.suggestedFolder)}
											<option value={item.suggestedFolder}>/{item.suggestedFolder} ★ Suggested</option>
										{/if}
										{#each folderPaths as path (path)}
											<option value={path}>
												/{path} {path === item.suggestedFolder ? '★ Suggested' : ''}
											</option>
										{/each}
										<option disabled>───────────────</option>
										<option value="__NEW__">+ Create new folder…</option>
									</select>
									<button
										type="button"
										class="btn-new-folder-action"
										onclick={() => { item.isCreatingNewFolder = true; item.newFolderName = ''; }}
										title="Add new folder"
									>
										+ New folder
									</button>
								</div>
							</div>
						{:else}
							<!-- Text input ONLY shown when admin explicitly wants to add a new folder -->
							<div class="placement-folder-row">
								<label class="placement-field-label" for="new-folder-input-{item.documentId}">
									New folder:
								</label>
								<div class="new-folder-box">
									<Icon name="folder" size={14} />
									<input
										id="new-folder-input-{item.documentId}"
										type="text"
										class="new-folder-input"
										placeholder="e.g. Research/Cardio"
										bind:value={item.newFolderName}
										onkeydown={(e) => {
											if (e.key === 'Enter') {
												e.preventDefault();
												confirmSinglePlacement(item);
											} else if (e.key === 'Escape') {
												item.isCreatingNewFolder = false;
												item.selectedFolder = item.suggestedFolder;
											}
										}}
									/>
									<button
										type="button"
										class="btn-folder-cancel"
										onclick={() => {
											item.isCreatingNewFolder = false;
											item.selectedFolder = item.suggestedFolder;
										}}
									>
										Cancel
									</button>
								</div>
							</div>
						{/if}

						<!-- Tags & Category Assignment with AI Suggestions -->
						<div class="placement-tags-row">
							<span class="placement-field-label">
								Tags:
							</span>
							<div class="placement-tags-content">
								<!-- Selected tags pills & input -->
								<div class="placement-tags-editor">
									{#each item.selectedTags as tag (tag)}
										<span class="placement-tag-chip">
											<Icon name="tag" size={11} />
											<span>{tag}</span>
											<button
												type="button"
												class="tag-del-btn"
												onclick={() => removeTagFromPlacement(item, tag)}
												aria-label="Remove tag {tag}"
											>×</button>
										</span>
									{/each}
									<div class="placement-tag-input-wrap">
										<input
											type="text"
											class="placement-tag-input"
											placeholder="+ add tag..."
											list="known-tags-{item.documentId}"
											bind:value={item.newTagInput}
											onkeydown={(e) => {
												if (e.key === 'Enter') {
													e.preventDefault();
													addTagToPlacement(item, item.newTagInput);
												}
											}}
										/>
										{#if item.newTagInput.trim()}
											<button
												type="button"
												class="btn-add-tag-inline"
												onclick={() => addTagToPlacement(item, item.newTagInput)}
												aria-label="Add tag"
											>
												<Icon name="plus" size={11} />
											</button>
										{/if}
										<datalist id="known-tags-{item.documentId}">
											{#each allKnownTags as t (t)}
												<option value={t}></option>
											{/each}
										</datalist>
									</div>
								</div>

								<!-- AI Suggestions -->
								{#if item.suggestedTags && item.suggestedTags.length > 0}
									<div class="placement-ai-suggestions">
										<span class="ai-badge">
											<Icon name="sparkles" size={12} />
											AI suggested:
										</span>
										<div class="ai-suggestion-chips">
											{#each item.suggestedTags as tag (tag)}
												{@const isSelected = item.selectedTags.includes(tag)}
												<button
													type="button"
													class="ai-suggest-chip"
													class:selected={isSelected}
													onclick={() => toggleAiTagSuggestion(item, tag)}
													title={isSelected ? 'Click to remove AI suggested tag' : 'Click to add AI suggested tag'}
												>
													{#if isSelected}
														<Icon name="check" size={10} />
													{:else}
														<Icon name="plus" size={10} />
													{/if}
													<span>{tag}</span>
												</button>
											{/each}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>

					<div class="placement-card-actions">
						<button
							type="button"
							class="btn-dismiss-single"
							onclick={() => dismissFinalization(item.documentId)}
							title="Dismiss placement notification for this file"
						>
							<Icon name="x" size={12} />
							<span>Dismiss</span>
						</button>
						<button
							type="button"
							class="btn-confirm-single"
							onclick={() => confirmSinglePlacement(item)}
							title="Confirm destination and tags for this file"
						>
							<Icon name="check" size={13} />
							<span>Confirm</span>
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#snippet footer()}
		<div class="placement-dialog-footer">
			<Button variant="ghost" onclick={() => (placementDialogOpen = false)}>
				Decide later ({pendingPlacements.length})
			</Button>
			{#if pendingPlacements.length > 0}
				<Button variant="filled" onclick={confirmAllPlacements}>
					Confirm all ({pendingPlacements.length})
				</Button>
			{/if}
		</div>
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
	.dropzone { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: .3rem; min-height: 8rem; padding: var(--space-4); text-align: center; cursor: pointer; border: 2px dashed var(--line-2); border-radius: 16px; background: var(--panel-2); transition: border-color .15s var(--ease), background .15s var(--ease); border-color: var(--line-2); }
	.dropzone:hover, .dropzone:focus-visible { border-color: var(--accent); outline: none; }
	.dropzone.dragover { border-color: var(--accent); background: var(--accent-soft); }
	.dropzone.has-file { cursor: default; padding: var(--space-3); }
	.dz-title { font-weight: 650; }
	.dz-filename { font-weight: 650; font-size: var(--text-sm); margin-top: .3rem; }
	.dz-actions { display: flex; justify-content: flex-end; gap: var(--space-2); }
	.multi-file-summary { display: flex; align-items: center; gap: .5rem; font-weight: 600; color: var(--ink); }
	.multi-count { color: var(--accent-ink); }
	.multi-size { font-size: var(--text-xs); color: var(--muted); font-weight: 400; }
	.multi-file-list { display: flex; flex-direction: column; gap: .25rem; width: 100%; max-height: 10.5rem; overflow-y: auto; background: var(--panel); border: 1px solid var(--line); border-radius: var(--r); padding: .35rem; margin: .35rem 0; }
	.multi-file-item { display: flex; align-items: center; gap: .4rem; padding: .25rem .45rem; background: var(--panel-2); border-radius: 6px; font-size: var(--text-xs); color: var(--ink); }
	.multi-name { flex: 1 1 auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: left; }
	.multi-kb { color: var(--muted); font-size: .65rem; flex: 0 0 auto; }
	.multi-del { border: none; background: none; cursor: pointer; color: var(--muted); font-size: 1rem; line-height: 1; padding: 0 .15rem; }
	.multi-del:hover { color: var(--danger); }
	.multi-add-more { margin: 0; font-size: var(--text-xs); color: var(--accent); font-weight: 500; }
	.target-folder-notice { display: flex; align-items: center; gap: .4rem; padding: .35rem .65rem; background: var(--panel-2); border: 1px solid var(--line); border-radius: var(--r); font-size: var(--text-xs); color: var(--ink-2); margin-top: .4rem; }
	.target-folder-notice strong { color: var(--accent-ink); }
	.multi-progress { display: flex; flex-direction: column; gap: .25rem; margin-top: .4rem; }
	.multi-progress-head { display: flex; align-items: center; justify-content: space-between; font-size: var(--text-xs); color: var(--ink-2); }
	.multi-curr-file { color: var(--muted); font-size: .68rem; max-width: 14rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.bar-track { height: 6px; background: var(--line); border-radius: 9999px; overflow: hidden; }
	.bar-fill { height: 100%; background: var(--accent); transition: width .2s var(--ease); }
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
	.graph-stats { margin: 0 0 var(--space-4); }
	.menu-choice.menu-active { color: var(--accent-ink); background: var(--accent-soft); }
	.access-list { max-height: 50vh; overflow-y: auto; display: grid; gap: .4rem; list-style: none; padding: 0; }
	.access-list label { display: flex; align-items: center; gap: .5rem; }
	.move-suggestions { display: flex; flex-wrap: wrap; gap: .3rem; margin-top: .3rem; }

	/* --- Notification button in toolbar for pending placements (specs/v15/05) --- */
	.tb-placement-notify {
		display: inline-flex;
		align-items: center;
		gap: .45rem;
		padding: .4rem .75rem;
		border-radius: 10px;
		border: 1px solid color-mix(in srgb, var(--accent) 45%, var(--line));
		background: color-mix(in srgb, var(--accent) 12%, var(--panel));
		color: var(--accent-ink);
		font-size: var(--text-xs);
		font-weight: 650;
		cursor: pointer;
		transition: all .18s var(--ease);
		position: relative;
	}
	.tb-placement-notify:hover {
		background: color-mix(in srgb, var(--accent) 22%, var(--panel));
		border-color: var(--accent);
		transform: translateY(-1px);
	}
	.tb-placement-notify.active {
		background: var(--accent);
		color: #ffffff;
		border-color: var(--accent);
	}
	.notify-icon-wrap {
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}
	.notify-ping {
		position: absolute;
		top: -2px;
		right: -2px;
		width: 7px;
		height: 7px;
		border-radius: 9999px;
		background: #ef4444;
		box-shadow: 0 0 0 2px var(--panel);
		animation: pulse-ping 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}
	@keyframes pulse-ping {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: .7; transform: scale(1.15); }
	}
	.notify-count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 1.25rem;
		height: 1.25rem;
		padding: 0 .35rem;
		border-radius: 9999px;
		background: var(--accent);
		color: #ffffff;
		font-size: .68rem;
		font-weight: 700;
	}
	.tb-placement-notify.active .notify-count {
		background: #ffffff;
		color: var(--accent);
	}

	/* --- Placement dialog layout & item cards (specs/v15/05) --- */
	.placements-header-hint { margin: 0 0 .85rem; font-size: var(--text-sm); color: var(--ink-2); }
	.empty-placements { text-align: center; padding: 2rem 1rem; color: var(--muted); display: flex; flex-direction: column; align-items: center; gap: .5rem; }
	.placement-list {
		display: flex;
		flex-direction: column;
		gap: .75rem;
		max-height: 25rem;
		overflow-y: auto;
		padding-right: .25rem;
		margin: .35rem 0;
	}
	.placement-card {
		background: var(--panel-2);
		border: 1px solid var(--line);
		border-radius: var(--r);
		padding: .75rem 1rem;
		display: flex;
		flex-direction: column;
		gap: .65rem;
		transition: border-color .15s var(--ease);
	}
	.placement-card:hover {
		border-color: color-mix(in srgb, var(--accent) 40%, var(--line));
	}
	.placement-card-header {
		display: flex;
		align-items: flex-start;
		gap: .65rem;
	}
	.placement-file-icon {
		color: var(--accent);
		display: inline-flex;
		align-items: center;
		padding-top: .15rem;
		flex-shrink: 0;
	}
	.placement-file-title-wrap {
		display: flex;
		flex-direction: column;
		gap: .25rem;
		flex: 1 1 auto;
		min-width: 0;
	}
	.placement-file-title {
		font-size: var(--text-sm);
		font-weight: 650;
		color: var(--ink);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.placement-meta-row {
		display: flex;
		align-items: center;
		gap: .4rem;
		flex-wrap: wrap;
	}
	.placement-chip {
		display: inline-flex;
		align-items: center;
		gap: .25rem;
		padding: .15rem .45rem;
		border-radius: 9999px;
		font-size: .68rem;
		font-weight: 600;
	}
	.placement-chip.type {
		background: color-mix(in srgb, var(--line) 60%, transparent);
		color: var(--ink-2);
	}
	.placement-chip.suggested {
		background: color-mix(in srgb, var(--accent) 14%, var(--panel));
		color: var(--accent-ink);
		border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
	}
	.placement-chip.suggested.root {
		background: color-mix(in srgb, var(--line) 40%, var(--panel));
		color: var(--ink-2);
		border-color: var(--line);
	}
	.placement-chip.ai-tags-badge {
		background: color-mix(in srgb, #8b5cf6 15%, var(--panel));
		color: #7c3aed;
		border: 1px solid color-mix(in srgb, #8b5cf6 35%, transparent);
	}
	.placement-card-body {
		background: var(--panel);
		border: 1px solid var(--line);
		border-radius: 8px;
		padding: .5rem .75rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: .65rem;
		flex-wrap: wrap;
	}
	.placement-folder-row {
		display: flex;
		align-items: center;
		gap: .55rem;
		flex: 1 1 auto;
		flex-wrap: wrap;
	}
	.placement-field-label {
		font-size: var(--text-xs);
		font-weight: 600;
		color: var(--muted);
		min-width: 5.5rem;
		flex-shrink: 0;
	}
	.placement-select-group {
		display: flex;
		align-items: center;
		gap: .4rem;
		flex: 1 1 auto;
		min-width: 14rem;
	}
	.placement-dropdown {
		flex: 1 1 auto;
		padding: .35rem .65rem;
		border: 1px solid var(--line);
		border-radius: 6px;
		background: var(--panel-2);
		color: var(--ink);
		font-size: var(--text-xs);
		font-weight: 500;
		cursor: pointer;
	}
	.btn-new-folder-action {
		display: inline-flex;
		align-items: center;
		gap: .25rem;
		padding: .35rem .6rem;
		border: 1px dashed var(--line-2);
		border-radius: 6px;
		background: transparent;
		color: var(--ink-2);
		font-size: var(--text-xs);
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
		transition: all .15s var(--ease);
	}
	.btn-new-folder-action:hover {
		background: var(--panel-2);
		border-color: var(--accent);
		color: var(--accent-ink);
	}
	.new-folder-box {
		display: flex;
		align-items: center;
		gap: .4rem;
		flex: 1 1 auto;
	}
	.new-folder-input {
		flex: 1 1 auto;
		padding: .35rem .65rem;
		border: 1px solid var(--accent);
		border-radius: 6px;
		background: var(--panel);
		color: var(--ink);
		font-size: var(--text-xs);
		font-weight: 500;
	}
	.btn-folder-cancel {
		padding: .3rem .55rem;
		border: 1px solid var(--line);
		border-radius: 6px;
		background: var(--panel-2);
		color: var(--muted);
		font-size: var(--text-xs);
		cursor: pointer;
	}
	.btn-folder-cancel:hover {
		color: var(--ink);
	}
	.placement-tags-row {
		display: flex;
		align-items: flex-start;
		gap: .55rem;
		flex: 1 1 auto;
		width: 100%;
		padding-top: .4rem;
		border-top: 1px dashed color-mix(in srgb, var(--line) 70%, transparent);
	}
	.placement-tags-content {
		display: flex;
		flex-direction: column;
		gap: .45rem;
		flex: 1 1 auto;
		min-width: 0;
	}
	.placement-tags-editor {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: .35rem;
	}
	.placement-tag-chip {
		display: inline-flex;
		align-items: center;
		gap: .3rem;
		padding: .2rem .55rem;
		background: color-mix(in srgb, var(--panel-2) 90%, white);
		border: 1px solid var(--line-2);
		border-radius: 9999px;
		font-size: .72rem;
		font-weight: 550;
		color: var(--ink);
	}
	.tag-del-btn {
		border: none;
		background: none;
		cursor: pointer;
		font-size: .9rem;
		line-height: 1;
		color: var(--muted);
		padding: 0;
		margin-left: 2px;
	}
	.tag-del-btn:hover {
		color: var(--danger);
	}
	.placement-tag-input-wrap {
		display: inline-flex;
		align-items: center;
		gap: .25rem;
	}
	.placement-tag-input {
		padding: .2rem .5rem;
		border: 1px dashed var(--line-2);
		border-radius: 9999px;
		background: var(--panel);
		color: var(--ink);
		font-size: .72rem;
		width: 7.5rem;
		transition: all .15s ease;
	}
	.placement-tag-input:focus {
		outline: none;
		border-color: var(--accent);
		width: 9.5rem;
		border-style: solid;
	}
	.btn-add-tag-inline {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.35rem;
		height: 1.35rem;
		border-radius: 50%;
		border: 1px solid var(--accent);
		background: var(--accent-soft);
		color: var(--accent-ink);
		cursor: pointer;
		padding: 0;
	}
	.placement-ai-suggestions {
		display: flex;
		align-items: center;
		gap: .45rem;
		flex-wrap: wrap;
	}
	.ai-badge {
		display: inline-flex;
		align-items: center;
		gap: .25rem;
		font-size: .68rem;
		font-weight: 650;
		color: #7c3aed;
		background: color-mix(in srgb, #8b5cf6 10%, transparent);
		padding: .15rem .45rem;
		border-radius: 6px;
	}
	.ai-suggestion-chips {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: .3rem;
	}
	.ai-suggest-chip {
		display: inline-flex;
		align-items: center;
		gap: .25rem;
		padding: .15rem .5rem;
		border-radius: 9999px;
		border: 1px dashed color-mix(in srgb, #8b5cf6 40%, var(--line));
		background: color-mix(in srgb, #8b5cf6 6%, var(--panel));
		color: var(--ink-2);
		font-size: .68rem;
		font-weight: 550;
		cursor: pointer;
		transition: all .15s ease;
	}
	.ai-suggest-chip:hover {
		border-color: #7c3aed;
		color: #7c3aed;
		background: color-mix(in srgb, #8b5cf6 14%, var(--panel));
	}
	.ai-suggest-chip.selected {
		border-style: solid;
		border-color: #7c3aed;
		background: color-mix(in srgb, #8b5cf6 18%, var(--panel));
		color: #6d28d9;
		font-weight: 650;
	}
	.placement-card-actions {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: .5rem;
	}
	.btn-dismiss-single {
		display: inline-flex;
		align-items: center;
		gap: .3rem;
		padding: .35rem .65rem;
		border-radius: 6px;
		background: var(--panel-2);
		border: 1px solid var(--line);
		color: var(--muted);
		font-size: var(--text-xs);
		font-weight: 550;
		cursor: pointer;
		transition: all .15s var(--ease);
	}
	.btn-dismiss-single:hover {
		background: var(--danger-soft);
		border-color: color-mix(in srgb, var(--danger) 40%, var(--line));
		color: var(--danger);
	}
	.btn-confirm-single {
		display: inline-flex;
		align-items: center;
		gap: .3rem;
		padding: .35rem .75rem;
		border-radius: 6px;
		background: color-mix(in srgb, var(--accent) 15%, var(--panel));
		border: 1px solid color-mix(in srgb, var(--accent) 40%, var(--line));
		color: var(--accent-ink);
		font-size: var(--text-xs);
		font-weight: 600;
		cursor: pointer;
		transition: all .15s var(--ease);
	}
	.btn-confirm-single:hover {
		background: var(--accent);
		color: #ffffff;
	}
	.placement-dialog-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
	}

	/* ══ Studio Finder Window Chrome (Radical Redesign) ═══════════════ */
	.finder {
		flex: 1 1 auto;
		min-width: 0;
		display: flex;
		flex-direction: column;
		min-height: calc(100dvh - 2 * var(--sheet-inset));
		background: transparent;
	}
	.finder-toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		flex-wrap: wrap;
		position: sticky;
		top: 0;
		z-index: 20;
		margin: 0;
		padding: 1.15rem var(--space-6);
		min-height: 4.8rem;
		background: color-mix(in srgb, var(--panel) 82%, var(--bg));
		backdrop-filter: blur(24px) saturate(180%);
		-webkit-backdrop-filter: blur(24px) saturate(180%);
		border-bottom: 1px solid color-mix(in srgb, var(--line) 75%, transparent);
	}
	.tb-actions {
		display: flex;
		align-items: center;
		gap: .65rem;
		flex-wrap: wrap;
		margin-left: auto;
	}
	.back-nav-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.35rem;
		height: 2.35rem;
		border-radius: 12px;
		border: 1px solid var(--line-2);
		background: var(--panel);
		color: var(--ink-2);
		cursor: pointer;
		transition: all .18s var(--ease);
	}
	.back-nav-btn:hover {
		background: var(--panel-2);
		border-color: var(--accent);
		color: var(--accent-ink);
		transform: scale(1.05);
	}
	.back-nav-btn :global(svg) { transform: rotate(90deg); }
	.window-switcher {
		display: inline-flex;
		align-items: center;
		background: color-mix(in srgb, var(--line) 40%, var(--panel-2));
		border: 1px solid var(--line-2);
		border-radius: 12px;
		padding: 3px;
		gap: 3px;
	}
	.ws-btn {
		display: inline-flex;
		align-items: center;
		gap: .4rem;
		padding: .4rem .75rem;
		border: none;
		background: none;
		color: var(--muted);
		font-size: var(--text-xs);
		font-weight: 600;
		border-radius: 9px;
		cursor: pointer;
		transition: all .15s ease;
		white-space: nowrap;
	}
	.ws-btn:hover {
		color: var(--ink);
	}
	.ws-btn.active {
		color: var(--accent-ink);
		background: var(--panel);
	}
	.tb-view-toggle {
		display: flex;
		border: 1px solid var(--line-2);
		border-radius: 12px;
		overflow: hidden;
		background: color-mix(in srgb, var(--line) 40%, var(--panel-2));
		padding: 3px;
		gap: 3px;
	}
	.tb-view-toggle button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		border: none;
		background: none;
		color: var(--muted);
		cursor: pointer;
		border-radius: 9px;
		transition: all .15s ease;
	}
	.tb-view-toggle button:hover { color: var(--ink); }
	.tb-view-toggle button.on {
		color: var(--accent-ink);
		background: var(--panel);
	}
	.tb-search {
		display: flex;
		align-items: center;
		gap: .45rem;
		border: 1px solid var(--line-2);
		border-radius: 99px;
		background: color-mix(in srgb, var(--panel) 90%, var(--panel-2));
		color: var(--muted);
		padding: .45rem .95rem;
		min-width: 16rem;
		transition: all .2s var(--ease);
	}
	.tb-search:focus-within {
		border-color: var(--accent);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 22%, transparent);
		background: var(--panel);
		color: var(--accent);
	}
	.tb-search input {
		border: none;
		background: none;
		font: inherit;
		font-size: var(--text-sm);
		color: var(--ink);
		min-width: 0;
		flex: 1 1 auto;
		outline: none;
	}
	.search-clear {
		border: none;
		background: none;
		cursor: pointer;
		font-size: 1.1rem;
		line-height: 1;
		color: var(--muted);
		padding: 0;
	}
	.search-clear:hover { color: var(--danger); }

	/* Interactive Breadcrumb Ribbon */
	.pathbar {
		display: flex;
		align-items: center;
		gap: .35rem;
		padding: .9rem var(--space-6) .3rem;
		font-size: var(--text-sm);
		flex-wrap: wrap;
		background: none;
	}
	.pathbar :global(svg) { flex: 0 0 auto; color: var(--muted); }
	.crumb {
		display: flex;
		align-items: center;
		gap: .35rem;
		border: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
		background: color-mix(in srgb, var(--panel) 80%, transparent);
		cursor: pointer;
		font: inherit;
		color: var(--accent-ink);
		padding: .28rem .7rem;
		border-radius: 99px;
		font-weight: 550;
		transition: all .15s ease;
		backdrop-filter: blur(8px);
	}
	.crumb:hover:not(:disabled) {
		background: var(--accent-soft);
		border-color: color-mix(in srgb, var(--accent) 40%, transparent);
		transform: translateY(-1px);
	}
	.crumb:disabled {
		color: var(--ink);
		cursor: default;
		font-weight: 650;
		background: color-mix(in srgb, var(--panel) 92%, white);
		border-color: var(--line-2);
	}
	.crumb.drag-target, .icon-tile.drag-target, .folder-tr.drag-target {
		border-color: var(--accent);
		background: var(--accent-soft);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 25%, transparent);
		transform: scale(1.04);
	}

	.status-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: .6rem;
		padding: .5rem 1rem;
		background: color-mix(in srgb, var(--panel) 94%, var(--bg));
		margin: .4rem var(--space-6) 0;
		border: 1px solid var(--line);
		border-radius: 14px;
		backdrop-filter: blur(12px);
	}
	.status-action {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--line);
		background: var(--panel);
		cursor: pointer;
		color: var(--ink-2);
		padding: .35rem .6rem;
		border-radius: 8px;
		font-size: var(--text-xs);
		font-weight: 550;
		gap: .35rem;
		transition: all .15s ease;
	}
	.status-action:hover {
		background: var(--panel-2);
		border-color: var(--accent);
		color: var(--accent-ink);
	}
	.retry-link {
		border: none;
		background: none;
		color: var(--accent-ink);
		cursor: pointer;
		font: inherit;
		padding: 0;
		text-decoration: underline;
		font-weight: 600;
	}

	.finder-body {
		display: flex;
		flex: 1 1 auto;
		min-height: 0;
		gap: var(--space-4);
		padding: var(--space-3) var(--space-6) var(--space-5);
	}
	.finder-content {
		position: relative;
		flex: 1 1 auto;
		min-width: 0;
		overflow-y: auto;
		scrollbar-gutter: stable;
		background: color-mix(in srgb, var(--panel) 94%, var(--bg));
		border: 1px solid var(--portal-surface-border);
		border-radius: 20px;
		box-shadow: var(--shadow);
		transition: all var(--duration-fast);
	}
	.list-empty { grid-column: 1 / -1; padding: var(--space-7) var(--space-4); width: 100%; text-align: center; }
	.graph-pane { padding: var(--space-4); height: 100%; display: flex; flex-direction: column; }
	.finder-sidebar {
		position: relative;
		width: 15rem;
		flex: 0 0 auto;
		background: color-mix(in srgb, var(--panel) 88%, var(--bg));
		padding: var(--space-4);
		overflow-y: auto;
		scrollbar-gutter: stable;
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border: 1px solid var(--portal-surface-border);
		border-radius: 20px;
		box-shadow: var(--shadow);
		transition: all var(--duration-fast);
	}
	.finder-content.external-dragover,
	.finder-sidebar.external-dragover {
		border-color: var(--accent);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 30%, transparent), var(--shadow-lg);
	}
	.drop-overlay {
		position: absolute;
		inset: 0;
		z-index: 40;
		display: flex;
		align-items: center;
		justify-content: center;
		background: color-mix(in srgb, var(--panel) 84%, var(--accent));
		border: 2px dashed var(--accent);
		border-radius: 20px;
		pointer-events: none;
		backdrop-filter: blur(6px);
		-webkit-backdrop-filter: blur(6px);
	}
	.drop-pill {
		display: flex;
		align-items: center;
		gap: .65rem;
		padding: .85rem 1.45rem;
		background: var(--panel);
		color: var(--accent-ink);
		border: 1px solid var(--accent);
		border-radius: 9999px;
		font-weight: 650;
		font-size: var(--text-sm);
		box-shadow: var(--shadow-lg);
		pointer-events: none;
	}
	.drop-overlay.sidebar-overlay {
		border-radius: 20px;
		padding: var(--space-2);
	}
	.drop-overlay.sidebar-overlay .drop-pill {
		padding: .5rem .85rem;
		font-size: var(--text-xs);
		gap: .4rem;
	}
	.sidebar-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: .3rem;
		margin-bottom: .6rem;
		padding-bottom: .4rem;
		border-bottom: 1px solid var(--line);
	}
	.tree-root {
		display: flex;
		align-items: center;
		gap: .45rem;
		border: none;
		background: none;
		cursor: pointer;
		font: inherit;
		color: var(--ink);
		padding: .45rem .6rem;
		flex: 1 1 auto;
		min-width: 0;
		text-align: left;
		border-radius: 10px;
		font-weight: 650;
		font-size: var(--text-sm);
		transition: all .15s ease;
	}
	.tree-root:hover, .tree-root.active {
		color: var(--accent-ink);
		background: var(--accent-soft);
	}
	.sidebar-collapse, .sidebar-expand {
		display: flex;
		align-items: center;
		justify-content: center;
		flex: 0 0 auto;
		width: 1.8rem;
		height: 1.8rem;
		border: 1px solid var(--line-2);
		background: var(--panel);
		color: var(--muted);
		cursor: pointer;
		border-radius: 8px;
		transition: all .15s ease;
	}
	.sidebar-collapse:hover, .sidebar-expand:hover {
		background: var(--panel-2);
		color: var(--ink);
		border-color: var(--accent);
	}
	.sidebar-collapse :global(svg) { transform: rotate(180deg); }
	.sidebar-expand {
		align-self: flex-start;
		margin: var(--space-2) 0 0 .2rem;
		box-shadow: var(--shadow);
	}

	/* ── Studio Resource Card Grid ── */
	.finder-content.grid-mode { padding: var(--space-4); }
	.icon-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(10.5rem, 1fr));
		gap: 1.1rem;
		padding: .5rem;
		transition: all .2s var(--ease);
	}
	.icon-grid.size-medium {
		grid-template-columns: repeat(auto-fill, minmax(8.25rem, 1fr));
		gap: .85rem;
		padding: .4rem;
	}
	.icon-grid.size-small {
		grid-template-columns: repeat(auto-fill, minmax(6.25rem, 1fr));
		gap: .6rem;
		padding: .3rem;
	}
	.icon-tile {
		display: flex;
		flex-direction: column;
		align-items: center;
		text-align: center;
		gap: .5rem;
		padding: 1rem .85rem .95rem;
		border: 1px solid var(--line);
		background: var(--panel);
		cursor: pointer;
		border-radius: 18px;
		position: relative;
		transition: all .2s var(--ease);
	}
	.icon-grid.size-medium .icon-tile {
		padding: .7rem .6rem .75rem;
		border-radius: 14px;
		gap: .35rem;
	}
	.icon-grid.size-small .icon-tile {
		padding: .5rem .45rem .55rem;
		border-radius: 11px;
		gap: .25rem;
	}
	.icon-tile:hover {
		background: color-mix(in srgb, var(--panel) 98%, white);
		border-color: var(--line-2);
		transform: translateY(-3px);
	}
	.icon-tile.on, .icon-tile.selected {
		background: var(--accent-soft);
		border-color: var(--accent);
		box-shadow: 0 0 0 2px var(--accent);
	}
	.icon-tile.selected .tile-label { color: var(--accent-ink); }
	.tile-select-check {
		width: 1rem;
		height: 1rem;
		border-radius: 4px;
		accent-color: var(--accent);
		cursor: pointer;
		opacity: 0;
		transition: opacity .15s ease;
	}
	.icon-tile:hover .tile-select-check,
	.tile-select-check.visible {
		opacity: 1;
	}
	.tile-header-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		min-height: 1.25rem;
	}
	.file-ext-tag, .badge-tag {
		font-size: .62rem;
		font-weight: 750;
		letter-spacing: .05em;
		padding: .15rem .45rem;
		border-radius: 6px;
		background: color-mix(in srgb, var(--line) 70%, var(--panel-2));
		color: var(--ink-2);
	}
	.badge-tag.ingest {
		background: color-mix(in srgb, var(--accent) 15%, var(--panel));
		color: var(--accent-ink);
	}
	.badge-tag.err {
		background: var(--danger-soft);
		color: var(--danger);
	}
	.tile-badges {
		display: flex;
		align-items: center;
		gap: .3rem;
	}
	.tile-badge {
		width: 1.2rem;
		height: 1.2rem;
		border-radius: 50%;
		background: var(--panel);
		border: 1px solid var(--line);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--muted);
	}
	.tile-badge.lock {
		color: var(--warn);
		background: var(--warn-soft);
		border-color: color-mix(in srgb, var(--warn) 35%, transparent);
	}
	.tile-badge.bell {
		color: var(--accent);
		background: var(--accent-soft);
		border-color: color-mix(in srgb, var(--accent) 35%, transparent);
	}
	.tile-art {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 4.25rem;
		height: 4.25rem;
		border-radius: 16px;
		margin: .2rem 0 .4rem;
		transition: transform .2s var(--ease), width .2s var(--ease), height .2s var(--ease);
	}
	.icon-grid.size-medium .tile-art {
		width: 3.2rem;
		height: 3.2rem;
		border-radius: 12px;
		margin: .1rem 0 .25rem;
	}
	.icon-grid.size-small .tile-art {
		width: 2.35rem;
		height: 2.35rem;
		border-radius: 9px;
		margin: 0 0 .15rem;
	}
	.icon-grid.size-medium .tile-label {
		font-size: .8rem;
		line-height: 1.25;
	}
	.icon-grid.size-small .tile-label {
		font-size: .72rem;
		line-height: 1.2;
	}
	.icon-grid.size-medium .tile-meta-pill {
		font-size: .62rem;
		padding: .1rem .45rem;
	}
	.icon-grid.size-medium .tile-footer-hint {
		font-size: .6rem;
	}
	.icon-grid.size-small .tile-meta-pill,
	.icon-grid.size-small .tile-footer-hint {
		display: none;
	}
	.icon-grid.size-small .tile-header-bar {
		min-height: 1rem;
	}
	.icon-grid.size-small .file-ext-tag,
	.icon-grid.size-small .badge-tag {
		font-size: .52rem;
		padding: .08rem .3rem;
		border-radius: 4px;
	}
	.icon-grid.size-small .tile-badge {
		width: .95rem;
		height: .95rem;
	}
	.icon-grid.size-small .tile-select-check {
		width: .85rem;
		height: .85rem;
	}
	.icon-grid.size-medium .file-ext-tag,
	.icon-grid.size-medium .badge-tag {
		font-size: .58rem;
		padding: .12rem .35rem;
	}
	.finder-content.size-medium .finder-table th,
	.finder-content.size-medium .finder-table td {
		padding: .5rem var(--space-3);
		font-size: var(--text-sm);
	}
	.finder-content.size-small .finder-table th,
	.finder-content.size-small .finder-table td {
		padding: .32rem var(--space-2);
		font-size: var(--text-xs);
	}
	.finder-content.size-medium .col-pane { width: 13.5rem; }
	.finder-content.size-medium .col-row { padding: .45rem .65rem; font-size: var(--text-sm); }
	.finder-content.size-small .col-pane { width: 12rem; padding: var(--space-2); }
	.finder-content.size-small .col-row { padding: .32rem .5rem; font-size: var(--text-xs); }
	.icon-tile:hover .tile-art { transform: scale(1.08); }
	.folder-art {
		background: color-mix(in srgb, #38bdf8 14%, var(--panel-2));
		color: #0284c7;
	}
	.tag-art {
		background: color-mix(in srgb, #8b5cf6 14%, var(--panel-2));
		color: #7c3aed;
	}
	.doc-art {
		background: color-mix(in srgb, var(--accent) 12%, var(--panel-2));
		color: var(--accent-ink);
	}
	.tile-label {
		font-size: var(--text-sm);
		font-weight: 600;
		color: var(--ink);
		line-height: 1.3;
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		word-break: break-word;
	}
	.icon-tile.on .tile-label { color: var(--accent-ink); }
	.tile-meta-pill {
		font-size: .68rem;
		font-weight: 550;
		color: var(--muted);
		background: var(--panel-2);
		border: 1px solid var(--line);
		border-radius: 99px;
		padding: .15rem .55rem;
		margin-top: auto;
	}
	.tile-footer-hint {
		font-size: .65rem;
		color: var(--muted);
		margin-top: auto;
		opacity: .8;
	}
	.tile-sub { font-size: .7rem; font-weight: 600; color: var(--danger); }
	.staged-tile {
		opacity: .95;
		background: color-mix(in srgb, var(--panel-2) 90%, white);
		cursor: context-menu;
	}
	.staged-tile.error {
		border-color: var(--danger);
		background: var(--danger-soft);
	}
	.staged-tile-footer {
		display: flex;
		gap: .35rem;
		margin-top: auto;
		width: 100%;
		justify-content: center;
	}
	.staged-pill-btn {
		font-size: .65rem;
		font-weight: 600;
		padding: .15rem .5rem;
		border-radius: 99px;
		background: var(--panel);
		border: 1px solid var(--line);
		color: var(--ink);
		cursor: pointer;
		transition: all .15s ease;
	}
	.staged-pill-btn:hover {
		background: var(--panel-2);
		border-color: var(--line-strong);
	}
	.staged-pill-btn.danger {
		color: var(--danger);
		background: var(--danger-soft);
		border-color: color-mix(in srgb, var(--danger) 30%, transparent);
	}
	.staged-pill-btn.danger:hover {
		background: var(--danger);
		color: white;
	}
	.staged-row-title {
		display: flex;
		align-items: center;
		gap: .5rem;
	}
	.staged-row-actions {
		display: flex;
		gap: .3rem;
	}
	.staged-table-btn {
		font-size: .7rem;
		font-weight: 600;
		padding: .2rem .55rem;
		border-radius: var(--radius-sm);
		background: var(--panel-2);
		border: 1px solid var(--line);
		color: var(--ink);
		cursor: pointer;
	}
	.staged-table-btn:hover {
		background: var(--panel);
	}
	.staged-table-btn.danger {
		color: var(--danger);
		background: var(--danger-soft);
		border-color: color-mix(in srgb, var(--danger) 30%, transparent);
	}
	.staged-table-btn.danger:hover {
		background: var(--danger);
		color: white;
	}
	.job-progress.tiny {
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: .3rem;
		margin-top: auto;
	}
	.job-progress.tiny .track {
		height: 5px;
		border-radius: 99px;
		background: var(--line);
		overflow: hidden;
	}
	.job-progress.tiny .fill {
		height: 100%;
		background: linear-gradient(90deg, var(--accent), var(--accent-ink));
		border-radius: 99px;
		transition: width .3s var(--ease);
	}
	.job-pct {
		font-size: .65rem;
		font-weight: 650;
		color: var(--accent-ink);
	}

	/* ── Studio Data Table (List View) ── */
	.finder-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: var(--text-sm); }
	.finder-table th {
		text-align: left;
		padding: .75rem var(--space-4);
		border-bottom: 1px solid var(--line);
		color: var(--muted);
		font-weight: 700;
		font-size: .72rem;
		letter-spacing: .05em;
		text-transform: uppercase;
		position: sticky;
		top: 0;
		z-index: 5;
		background: color-mix(in srgb, var(--panel) 94%, var(--bg));
		backdrop-filter: blur(12px);
	}
	.finder-table td {
		padding: .75rem var(--space-4);
		border-bottom: 1px solid color-mix(in srgb, var(--line) 60%, transparent);
		vertical-align: middle;
	}
	.finder-table td:first-child { width: 2.2rem; text-align: center; }
	.finder-table td:nth-child(2) { display: flex; align-items: center; gap: .6rem; font-weight: 550; }
	.folder-tr, .doc-tr { cursor: pointer; transition: background .12s var(--ease); }
	.folder-tr:hover, .doc-tr:hover { background: color-mix(in srgb, var(--panel-2) 90%, white); }
	.folder-tr.on, .doc-tr.on, .doc-tr.selected, .folder-tr.selected { background: var(--accent-soft) !important; }
	.col-row.selected { background: color-mix(in srgb, var(--accent) 14%, var(--panel)) !important; color: var(--accent-ink); }
	.marquee-selection-box {
		position: fixed;
		z-index: 9999;
		pointer-events: none;
		background: color-mix(in srgb, var(--accent) 18%, transparent);
		border: 1.5px solid var(--accent);
		border-radius: 4px;
	}
	.finder-content.marquee-active {
		user-select: none;
		-webkit-user-select: none;
	}
	:global(.ctx-header) {
		display: flex;
		flex-direction: column;
		gap: .2rem;
		padding: .4rem .7rem;
		font-size: .72rem;
		font-weight: 700;
		color: var(--muted);
		border-bottom: 1px solid var(--line);
		margin-bottom: .25rem;
		letter-spacing: .02em;
	}
	:global(.ctx-sub) {
		font-size: .65rem;
		font-weight: 500;
		color: var(--muted);
		display: block;
	}
	.job-progress { display: grid; gap: .25rem; width: 100%; }
	.job-progress .track { height: 4px; background: var(--panel); overflow: hidden; border-radius: 99px; }
	.job-progress .fill { height: 100%; background: var(--accent); transition: width .3s var(--ease); }
	.job-error { color: var(--danger); margin: 0; font-weight: 600; }

	/* ── Studio Miller Columns (Column View) ── */
	.column-view { display: flex; height: 100%; overflow-x: auto; scrollbar-gutter: stable; }
	.col-pane {
		width: 15rem;
		flex: 0 0 auto;
		border-right: 1px solid color-mix(in srgb, var(--line) 75%, transparent);
		overflow-y: auto;
		padding: var(--space-3);
		scrollbar-gutter: stable;
	}
	.col-row {
		display: flex;
		align-items: center;
		gap: .5rem;
		width: 100%;
		text-align: left;
		border: 1px solid transparent;
		background: none;
		cursor: pointer;
		font: inherit;
		font-size: var(--text-sm);
		color: var(--ink);
		padding: .45rem .65rem;
		border-radius: 10px;
		transition: all .15s ease;
	}
	.col-row:hover { background: var(--panel-2); }
	.col-row.active { background: var(--accent-soft); color: var(--accent-ink); font-weight: 600; }
	.col-row.drag-target { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }
	.col-row .row-sub { color: var(--muted); font-size: var(--text-xs); }
	.col-row :global(svg:last-child) { margin-left: auto; color: var(--muted); flex: 0 0 auto; }
	.col-row.doc :global(svg:first-child) { color: var(--muted); }
	.col-empty { padding: var(--space-3) .65rem; color: var(--muted); font-size: var(--text-sm); }

	/* ── Context Studio Inspector ── */
	.inspector {
		width: 22rem;
		flex: 0 0 auto;
		background: color-mix(in srgb, var(--panel) 95%, var(--bg));
		padding: var(--space-5);
		overflow-y: auto;
		scrollbar-gutter: stable;
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
		border: 1px solid var(--portal-surface-border);
		border-radius: 20px;
		box-shadow: var(--shadow-lg);
		transition: all var(--duration-fast);
	}
	.inspector-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-3);
		margin-bottom: .4rem;
	}
	.match-snippet {
		font-size: var(--text-sm);
		color: var(--ink-2);
		background: var(--panel-2);
		border: 1px solid var(--line);
		border-radius: var(--r);
		padding: var(--space-3);
		margin: var(--space-3) 0;
		line-height: 1.5;
	}
	.match-snippet :global(mark) {
		background: var(--accent-soft);
		color: var(--accent-ink);
		border-radius: 3px;
		padding: 1px 4px;
	}
	.inspector-head h2 {
		font-size: 1.15rem;
		font-weight: 700;
		letter-spacing: -.02em;
		color: var(--ink);
		line-height: 1.35;
	}
	.inspector-actions {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: .5rem;
		margin: var(--space-3) 0;
	}
	.icon-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		border: 1px solid var(--line);
		background: var(--panel);
		color: var(--ink-2);
		width: 2.35rem;
		height: 2.35rem;
		border-radius: 10px;
		padding: 0;
		text-decoration: none;
		transition: all .15s ease;
	}
	.icon-btn:hover {
		border-color: var(--accent);
		color: var(--accent-ink);
		background: var(--panel-2);
		transform: translateY(-1px);
	}
	.finalize-notice {
		display: flex;
		align-items: center;
		gap: .5rem;
		width: 100%;
		text-align: left;
		border: 1px solid var(--warn);
		background: var(--warn-soft);
		color: var(--ink);
		border-radius: 12px;
		padding: var(--space-3);
		margin-bottom: var(--space-4);
		cursor: pointer;
		font: inherit;
		font-size: var(--text-sm);
		font-weight: 550;
		transition: all .15s ease;
	}
	.finalize-notice:hover { transform: translateY(-1px); }
	.detail-fields {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
		gap: var(--space-3);
		margin-bottom: var(--space-4);
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: .35rem;
		margin-bottom: var(--space-4);
	}
	.field > span:first-child {
		font-size: .72rem;
		font-weight: 700;
		letter-spacing: .05em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.field select, .field input[type="text"], .field input[type="number"] {
		border: 1px solid var(--line-2);
		border-radius: 10px;
		background: var(--panel);
		color: var(--ink);
		padding: .5rem .75rem;
		font: inherit;
		font-size: var(--text-sm);
		transition: all .15s ease;
	}
	.field select:focus, .field input:focus {
		outline: none;
		border-color: var(--accent);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent);
	}
	.visibility-toggle {
		display: inline-flex;
		align-items: center;
		gap: .45rem;
		border: 1px solid var(--line-2);
		border-radius: 10px;
		padding: .5rem .75rem;
		cursor: pointer;
		font: inherit;
		font-size: var(--text-xs);
		font-weight: 650;
		width: fit-content;
		background: var(--ok-soft);
		color: var(--ok);
		border-color: color-mix(in srgb, var(--ok) 35%, transparent);
		transition: all .15s ease;
	}
	.visibility-toggle.is-private {
		background: var(--warn-soft);
		color: var(--warn);
		border-color: color-mix(in srgb, var(--warn) 35%, transparent);
	}
	.visibility-toggle:hover { transform: translateY(-1px); }
	.fchip {
		font: inherit;
		font-size: var(--text-sm);
		cursor: pointer;
		border: 1px solid var(--line);
		background: var(--panel-2);
		color: var(--ink);
		padding: .35rem .75rem;
		border-radius: 10px;
		display: inline-flex;
		align-items: center;
		gap: .4rem;
		transition: all .15s ease;
	}
	.fchip:hover { border-color: var(--accent); }
	.tags { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; }
	.tag {
		font: inherit;
		font-size: .72rem;
		font-weight: 550;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: .25rem;
		border: 1px solid var(--line);
		border-radius: 99px;
		background: var(--panel);
		color: var(--ink-2);
		padding: .2rem .65rem;
		transition: all .15s ease;
	}
	.tag:hover {
		border-color: var(--danger);
		color: var(--danger);
		background: var(--danger-soft);
	}
	.tag-input {
		font: inherit;
		font-size: .72rem;
		border: 1px dashed var(--line-2);
		border-radius: 99px;
		padding: .2rem .65rem;
		background: transparent;
		color: var(--ink);
		width: 6.5rem;
		transition: all .15s ease;
	}
	.tag-input:focus {
		outline: none;
		border-color: var(--accent);
		background: var(--panel);
		width: 9rem;
	}
	.view {
		font: inherit;
		font-size: var(--text-sm);
		font-weight: 650;
		cursor: pointer;
		border: 1px solid var(--line);
		background: var(--panel);
		color: var(--accent-ink);
		padding: .4rem .85rem;
		border-radius: 10px;
		transition: all .15s ease;
	}
	.view:hover {
		border-color: var(--accent);
		background: var(--accent-soft);
	}
	.view.danger { color: var(--danger); }
	.view.danger:hover {
		border-color: var(--danger);
		background: var(--danger-soft);
	}
	.view:disabled { opacity: .5; cursor: not-allowed; }
	.upload-progress {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		background: var(--panel-2);
		padding: .45rem;
		border-radius: 10px;
	}
	.upload-progress .bar {
		flex: 1 1 auto;
		height: 6px;
		background: var(--accent);
		border-radius: 99px;
		transition: width .2s var(--ease);
	}
	.upload-progress .hint {
		flex: 0 0 auto;
		padding-right: .5rem;
		white-space: nowrap;
	}

	/* --- Maintenance Progress Bar (specs/v15/16) --- */
	.maintenance-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding: .6rem 1.25rem;
		background: color-mix(in srgb, var(--accent) 8%, var(--panel));
		border-bottom: 1px solid color-mix(in srgb, var(--accent) 25%, var(--line));
		font-size: var(--text-sm);
		transition: all .2s ease;
		animation: m-slide-down .2s ease-out;
	}
	@keyframes m-slide-down {
		from { opacity: 0; transform: translateY(-8px); }
		to { opacity: 1; transform: translateY(0); }
	}
	.maintenance-bar.done {
		background: color-mix(in srgb, #10b981 10%, var(--panel));
		border-color: color-mix(in srgb, #10b981 30%, var(--line));
	}
	.maintenance-bar.error {
		background: color-mix(in srgb, #ef4444 10%, var(--panel));
		border-color: color-mix(in srgb, #ef4444 30%, var(--line));
	}
	.maintenance-bar-left {
		display: flex;
		align-items: center;
		gap: .75rem;
		flex: 1;
		min-width: 0;
	}
	.m-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--accent-soft);
		color: var(--accent-ink);
		flex-shrink: 0;
	}
	.maintenance-bar.done .m-icon {
		background: color-mix(in srgb, #10b981 18%, transparent);
		color: #059669;
	}
	.m-icon.spin {
		animation: m-spin 1.4s linear infinite;
	}
	@keyframes m-spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}
	.m-info {
		display: flex;
		flex-direction: column;
		gap: .3rem;
		flex: 1;
		min-width: 0;
	}
	.m-title-row {
		display: flex;
		align-items: center;
		gap: .5rem;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
	.m-kind-badge {
		font-size: .68rem;
		font-weight: 650;
		text-transform: uppercase;
		letter-spacing: .04em;
		padding: .1rem .4rem;
		border-radius: 4px;
		background: var(--accent-soft);
		color: var(--accent-ink);
		flex-shrink: 0;
	}
	.maintenance-bar.done .m-kind-badge {
		background: color-mix(in srgb, #10b981 20%, transparent);
		color: #059669;
	}
	.m-step-text {
		font-size: var(--text-xs);
		color: var(--ink-2);
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.m-track {
		height: 6px;
		border-radius: 9999px;
		background: color-mix(in srgb, var(--ink) 10%, transparent);
		overflow: hidden;
		position: relative;
		width: 100%;
		max-width: 480px;
	}
	.m-track.large {
		height: 9px;
		max-width: 100%;
	}
	.m-fill {
		height: 100%;
		border-radius: 9999px;
		background: linear-gradient(90deg, var(--accent), color-mix(in srgb, var(--accent) 70%, #3b82f6));
		transition: width .3s ease;
		position: relative;
		overflow: hidden;
	}
	.maintenance-bar.done .m-fill {
		background: #10b981;
	}
	.m-fill::after {
		content: '';
		position: absolute;
		top: 0; left: 0; right: 0; bottom: 0;
		background: linear-gradient(
			90deg,
			transparent,
			rgba(255, 255, 255, 0.4),
			transparent
		);
		animation: m-shimmer 2s infinite;
	}
	@keyframes m-shimmer {
		0% { transform: translateX(-100%); }
		100% { transform: translateX(100%); }
	}
	.m-actions {
		display: flex;
		align-items: center;
		gap: .6rem;
		flex-shrink: 0;
	}
	.m-percentage {
		font-size: var(--text-xs);
		font-weight: 650;
		color: var(--ink-2);
		min-width: 2.4rem;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.m-btn-details, .m-btn-stop {
		border: 1px solid var(--line);
		background: var(--panel);
		color: var(--ink-2);
		font-size: var(--text-xs);
		font-weight: 550;
		padding: .25rem .55rem;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all .15s ease;
	}
	.m-btn-details:hover {
		background: var(--accent-soft);
		color: var(--accent-ink);
		border-color: color-mix(in srgb, var(--accent) 40%, var(--line));
	}
	.m-btn-stop:hover {
		background: color-mix(in srgb, #ef4444 12%, var(--panel));
		color: #dc2626;
		border-color: color-mix(in srgb, #ef4444 40%, var(--line));
	}
	.m-btn-dismiss {
		background: none;
		border: none;
		font-size: 1.1rem;
		color: var(--muted);
		cursor: pointer;
		padding: 0 .2rem;
		line-height: 1;
	}
	.m-btn-dismiss:hover {
		color: var(--ink);
	}

	/* In-dialog maintenance styles */
	.dialog-maintenance-running {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding: .4rem 0;
	}
	.dialog-m-header {
		display: flex;
		align-items: center;
		gap: .75rem;
	}
	.dialog-m-titles strong {
		display: block;
		font-size: var(--text-sm);
		color: var(--ink);
	}
	.dialog-m-detail {
		margin: .15rem 0 0;
		font-size: var(--text-xs);
		color: var(--muted);
	}
	.dialog-m-progress {
		display: flex;
		flex-direction: column;
		gap: .4rem;
	}
	.dialog-m-pct-row {
		display: flex;
		justify-content: space-between;
		font-size: var(--text-xs);
		color: var(--muted);
		font-variant-numeric: tabular-nums;
	}
	.dialog-m-hint {
		margin: 0;
		font-size: var(--text-xs);
		color: var(--muted);
		font-style: italic;
	}

	.ws-label-short { display: none; }

	@media (max-width: 960px) {
		.finder-body { flex-direction: column; }
		.finder-sidebar {
			width: 100%;
			max-height: 260px;
		}
		.inspector {
			width: 100%;
			max-height: 60vh;
			border-top: 2px solid var(--accent);
		}
	}
	@media (max-width: 760px) {
		.finder-toolbar { padding: .75rem 1rem; gap: .6rem; }
		.finder-toolbar .head-title { min-width: 0; width: 100%; }
		.finder-toolbar .head-title > div { min-width: 0; overflow: hidden; }
		.finder-toolbar .head-title h1 { font-size: 1.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
		.finder-toolbar .head-title p { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: var(--text-xs); }
		.tb-actions { margin-left: 0; width: 100%; justify-content: flex-start; gap: .45rem; }
		.tb-search { width: 100%; min-width: 100%; order: 10; margin-top: .15rem; }
		.tb-placement-notify { font-size: var(--text-xs); padding: .35rem .6rem; }
		.tb-placement-notify .notify-label { display: none; }
	}
	@media (max-width: 640px) {
		.ws-label-full { display: none; }
		.ws-label-short { display: inline; }
	}
	@media (max-width: 480px) {
		.ws-btn { padding: .35rem .5rem; font-size: .7rem; }
		.pathbar { padding: .6rem 1rem .2rem; }
		.finder-body { padding: var(--space-2) var(--space-3) var(--space-4); }
	}

</style>
