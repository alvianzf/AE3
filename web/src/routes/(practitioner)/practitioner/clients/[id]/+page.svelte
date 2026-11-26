<script lang="ts">
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { get, post, del } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Icon from '$lib/components/Icon.svelte';
	import Button from '$lib/components/Button.svelte';
	import Select from '$lib/components/Select.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Tabs from '$lib/components/Tabs.svelte';
	import { chunkedUpload } from '$lib/chunkedUpload';
	import { fileDrop } from '$lib/fileDrop';

	let { data } = $props();
	// Split out of one long scroll into tabs (ux-implementation-spec.md#1) —
	// Overview (the Questionnaire Response) is what a practitioner should
	// see first on opening a client.
	let active = $state('overview');

	function fileUrl(fileId: string) {
		return `${PUBLIC_API_BASE}/api/me/clients/${data.client.id}/files/${fileId}`;
	}

	// --- Journey redesign: the client page is the hub, not one of several
	// equal-weight destinations. One status, one primary next action —
	// instead of six flat tabs with no sense of "what do I do next" and
	// no way to even start a consult without leaving this page entirely
	// (found live: Consult and Clients were two disconnected lists; to
	// talk to a client you had to leave their page and re-find them in a
	// separate one). ------------------------------------------------------
	let links = $state<any[]>(data.links ?? []);
	const finalReport = $derived(
		(data.documents ?? []).find((d: any) => d.kind === 'client_report' && d.status === 'final')
	);
	const hasAnySession = $derived((data.sessions ?? []).length > 0);
	const hasQuestionnaireResponse = $derived(!!data.intake?.response);
	const openQuestionnaireLink = $derived(
		links.find((l: any) => l.kind === 'questionnaire' && l.status !== 'submitted')
	);
	const status = $derived.by(() => {
		if (finalReport) return {
			label: 'Client Report ready', detail: 'Finalized — download the PDF and send it to your client.',
			cta: 'Open report', href: `/practitioner/consult?client=${data.client.id}&session=${finalReport.session_id}&pane=doc&kind=client_report`
		};
		if (hasAnySession) return {
			label: 'Consult in progress', detail: 'No report finalized yet.',
			cta: 'Continue consult', href: `/practitioner/consult?client=${data.client.id}`
		};
		if (hasQuestionnaireResponse) return {
			label: 'Ready for consult', detail: 'Intake form received — nothing scheduled yet.',
			cta: 'Start consult', href: `/practitioner/consult?client=${data.client.id}`
		};
		if (openQuestionnaireLink) return {
			label: 'Awaiting response', detail: 'An intake link was sent and not yet submitted.',
			cta: null
		};
		return {
			label: 'No intake sent', detail: 'Send one to get started with this client.',
			cta: 'Send an intake form', action: () => { active = 'intake'; showSendPicker = true; }
		};
	});

	// "Send a questionnaire" directly from this page — used to mean
	// leaving the client entirely, going to the separate Questionnaires
	// page, and re-finding this same client in a dropdown there.
	let showSendPicker = $state(false);
	let selectedQuestionnaireId = $state('');
	let sendingQuestionnaire = $state(false);
	const followupQuestionnaires = $derived((data.questionnaires ?? []).filter((q: any) => q.kind === 'followup'));
	async function sendQuestionnaire() {
		if (!selectedQuestionnaireId) return;
		sendingQuestionnaire = true;
		try {
			const result = await post(fetch, `/me/questionnaires/${selectedQuestionnaireId}/links`, {
				client_id: data.client.id
			});
			links = [result, ...links];
			showSendPicker = false;
			toast('Intake link created — copy it from the list below.');
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			sendingQuestionnaire = false;
		}
	}
	function linkUrl(l: any) {
		return `${window.location.origin}/intake/${l.token}`;
	}
	async function copyLinkUrl(l: any) {
		await navigator.clipboard.writeText(linkUrl(l));
		toast('Link copied.');
	}

	let uploadLinkUrl = $state('');
	let creatingUploadLink = $state(false);
	async function createUploadLink() {
		creatingUploadLink = true;
		try {
			const result = await post(fetch, `/me/clients/${data.client.id}/upload-links`, {});
			uploadLinkUrl = `${window.location.origin}${result.url}`;
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			creatingUploadLink = false;
		}
	}
	async function copyUploadLink() {
		await navigator.clipboard.writeText(uploadLinkUrl);
		toast('Link copied.');
	}

	// Before this, the only way a file reached a client's record was the
	// client-facing upload link — no path for the practitioner to attach
	// something themselves (a prior clinic's labs, a scanned referral)
	// on day one, before any link is ever sent. Direct practitioner-side
	// upload, mirroring the intake page's own direct-vs-chunked split.
	// Lives in the Record tab now (not a separate Files list) — every
	// upload becomes a Record entry itself (app/main.py's
	// _save_uploaded_file), so that's where the result actually lands.
	const DIRECT_UPLOAD_LIMIT = 20 * 1024 * 1024;
	let uploadingFile = $state(false);
	let fileInput: HTMLInputElement | undefined = $state();
	let dragOver = $state(false);

	function onFilesPicked(e: Event) {
		const picked = (e.target as HTMLInputElement).files;
		if (picked?.length) handleFiles(Array.from(picked));
	}

	async function reloadRecord() {
		const r = await get(fetch, `/me/clients/${data.client.id}/record`).catch(() => null);
		if (r) {
			entries = r.entries ?? [];
			clinicalState = r.clinical_state ?? [];
		}
	}

	async function handleFiles(picked: File[]) {
		uploadingFile = true;
		try {
			for (const file of picked) {
				if (file.size > DIRECT_UPLOAD_LIMIT) {
					await chunkedUpload(`/me/clients/${data.client.id}/files`, file);
				} else {
					const form = new FormData();
					form.set('file', file);
					const res = await fetch(`${PUBLIC_API_BASE}/api/me/clients/${data.client.id}/files`, {
						method: 'POST',
						credentials: 'include',
						body: form
					});
					if (!res.ok) throw new Error('Could not upload ' + file.name + '.');
				}
			}
			toast('File uploaded.');
			// Every upload now creates its own Record entry server-side —
			// reload Record so it shows up without a manual page refresh.
			// Its AI doc_type/summary/highlights classify in the background
			// (a few seconds, not instant) and show "Processing…" until the
			// next load picks them up.
			await reloadRecord();
		} catch (err: any) {
			toast(err.message || 'Could not upload the file.', 'alert');
		} finally {
			uploadingFile = false;
			if (fileInput) fileInput.value = '';
		}
	}

	// session_documents rows have no `filename` — this list used to fall
	// back to the raw `kind` string. The Consult Draft Editor makes these
	// rows real and user-facing, so the fallback is replaced outright
	// with a proper label, a draft/final pill, and a deep link back into
	// the document pane that produced it.
	const DOCUMENT_KIND_LABELS: Record<string, string> = {
		clinician_note: 'Practitioner Note',
		client_report: 'Client Report'
	};

	// A session's own generated documents, shown inline under it in the
	// Sessions tab — the separate top-level "Documents" tab these used to
	// live under was just this same list with an extra click, not a
	// different piece of information.
	const documentsBySession = $derived.by(() => {
		const map: Record<string, any[]> = {};
		for (const d of data.documents ?? []) {
			(map[d.session_id] ??= []).push(d);
		}
		return map;
	});

	// The consult pipeline's patient context (app/patient/context.py) has
	// always read conditions/medications/labs — nothing ever wrote them
	// until now (found live, 2026-09-14: every real client's recent_labs
	// was empty because there was no way to record one, not because none
	// existed). This panel is that missing write path.
	const KIND_LABELS: Record<string, string> = {
		protocol: 'Client Protocol (Phased)',
		lab: 'Lab / test result',
		condition: 'Condition',
		medication: 'Medication',
		note: 'Note',
		history: 'History',
		document: 'Document'
	};

	// Groups the unified Record timeline by what a practitioner actually
	// wants to scan together — "everything about this client's labs" in
	// one place, whether it came from a manual entry or an uploaded PDF —
	// rather than one flat chronological list of every kind mixed in.
	// "document" is upload-only (see vault.KINDS); "note"/"history" are the
	// older, pre-condition/medication kinds and group alongside it since
	// none of the three carry structured clinical meaning on their own.
	const KIND_TO_CATEGORY: Record<string, string> = {
		lab: 'lab', condition: 'condition', medication: 'medication', protocol: 'protocol',
		document: 'documents', note: 'documents', history: 'documents'
	};
	const CATEGORY_LABELS: Record<string, string> = {
		lab: 'Labs & Trends', condition: 'Conditions', medication: 'Medications',
		protocol: 'Protocols', documents: 'Documents & Notes'
	};
	const CATEGORY_ORDER = ['lab', 'condition', 'medication', 'protocol', 'documents'];

	// specs/v9 — what app/reasoning/document_insights.py classifies an
	// uploaded file as. Shown as a chip on any Record entry backed by a
	// file; a document with no ai_doc_type yet (background job pending or
	// failed) falls back to "Processing…" rather than a blank chip.
	const DOC_TYPE_LABELS: Record<string, string> = {
		lab_result: 'Lab result', imaging_report: 'Imaging report', clinical_note: 'Clinical note',
		prescription: 'Prescription', intake_form: 'Intake form', insurance: 'Insurance',
		referral: 'Referral', other: 'Document'
	};
	function trendArrow(trend: string | null) {
		return trend === 'rising' ? '↑' : trend === 'falling' ? '↓' : trend === 'stable' ? '→' : '';
	}
	function markerTone(flag: string | null) {
		if (flag === 'high' || flag === 'low') return 'warn';
		if (flag === 'in_range') return 'ok';
		return 'neutral';
	}
	// Legacy marker only — clients could once self-add record entries via
	// POST /api/me/entries, but that route no longer exists (clients have
	// no account to call it from). This only ever matches pre-removal rows;
	// kept so those render correctly, not because the write path still exists.
	const PATIENT_REPORTED_PREFIX = '[patient-reported] ';
	function entryText(content: string) {
		return content.startsWith(PATIENT_REPORTED_PREFIX)
			? content.slice(PATIENT_REPORTED_PREFIX.length)
			: content;
	}
	function isClientReported(content: string) {
		return content.startsWith(PATIENT_REPORTED_PREFIX);
	}
	let entries = $state<any[]>(data.record?.entries ?? []);
	let clinicalState = $state<any[]>(data.record?.clinical_state ?? []);
	let entryKind = $state('lab');
	let entryContent = $state('');
	let addingEntry = $state(false);
	let deletingEntry = $state<string | null>(null);

	const groupedEntries = $derived.by(() => {
		const map: Record<string, any[]> = {};
		for (const e of entries) {
			const cat = KIND_TO_CATEGORY[e.kind] ?? 'documents';
			(map[cat] ??= []).push(e);
		}
		return map;
	});

	async function addEntry(e: Event) {
		e.preventDefault();
		if (!entryContent.trim()) return;
		addingEntry = true;
		try {
			const entry = await post(fetch, `/me/clients/${data.client.id}/entries`, {
				kind: entryKind, content: entryContent.trim()
			});
			entries = [entry, ...entries];
			entryContent = '';
			toast(`${KIND_LABELS[entryKind]} added to the record.`);
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			addingEntry = false;
		}
	}

	async function removeEntry(id: string) {
		deletingEntry = id;
		try {
			await del(fetch, `/me/clients/${data.client.id}/entries/${id}`);
			entries = entries.filter((e) => e.id !== id);
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			deletingEntry = null;
		}
	}

	// POST .../summary has existed since v1 (app/llm.py's summarize_session())
	// but had no UI anywhere to reach it — specs/v4/04-known-issues.md#h6.
	// specs/v4.1/03 CR3 — the toast claimed "saved to the client record" but
	// nothing re-read it on load, so a real, persisted summary looked gone
	// after a reload. Seed from data.sessions[*].summary (now returned by
	// GET .../sessions, backed by record_entries.session_id) instead of
	// only ever holding it in this component's own runtime state.
	// The intake GET route (app/main.py me_get_intake) was always fetched
	// here but never rendered — opening this page marked the questionnaire
	// "viewed" (app/vault.py mark_intake_viewed) without ever showing the
	// practitioner the answers that triggered that flag. This is that
	// missing render (journey-audit finding #1).
	function formatAnswer(q: any, value: any) {
		if (q.input_type === 'multi_choice') {
			return Array.isArray(value) && value.length ? value.join(', ') : '—';
		}
		return value === undefined || value === null || value === '' ? '—' : String(value);
	}

	let summarizing = $state<string | null>(null);
	let summaries = $state<Record<string, string>>(
		Object.fromEntries((data.sessions ?? []).filter((s: any) => s.summary).map((s: any) => [s.id, s.summary]))
	);

	async function summarize(sessionId: string) {
		summarizing = sessionId;
		try {
			const res = await post(fetch, `/me/clients/${data.client.id}/sessions/${sessionId}/summary`);
			summaries = { ...summaries, [sessionId]: res.summary };
			toast('Session summary saved to the client record.');
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			summarizing = null;
		}
	}
</script>

<svelte:head><title>{data.client.name} — Practitioner portal</title></svelte:head>

<div class="pane-row"><div class="detail-pane"><div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="user-card" size={16} /></span><h1>{data.client.name}</h1></div></div>
	<p><strong>{data.client.name}</strong> — {data.client.email}</p>
	<p class="hint">{data.client.country ?? 'Country not set'} · DOB {data.client.dob ?? 'not set'}</p>

	<div class="status-banner">
		<div class="status-text">
			<div class="status-label">{status.label}</div>
			<p class="hint status-detail">{status.detail}</p>
		</div>
		{#if status.cta && status.href}
			<Button href={status.href}>{status.cta}</Button>
		{:else if status.cta && status.action}
			<Button onclick={status.action}>{status.cta}</Button>
		{/if}
	</div>

	<div class="tabbar">
		<Tabs bind:active tabs={[
			{ id: 'overview', label: 'Overview' },
			{ id: 'intake', label: 'Intake Links' },
			{ id: 'record', label: 'Record' },
			{ id: 'sessions', label: 'Sessions' }
		]} />
	</div>

	{#if active === 'overview'}
		{#if data.intake?.response}
			<div class="rail-section intake-panel">
				<h2>Intake Response</h2>
				<p class="hint">Submitted {data.intake.response.submitted_at?.slice(0, 10) ?? ''}</p>
				<ul class="list intake-answers">
					{#each (data.intake.questionnaire?.questions ?? []).filter((q: any) => q.input_type !== 'info') as q (q.id)}
						<li class="intake-answer">
							<div class="iq-prompt">{q.prompt}</div>
							{#if q.input_type === 'repeater'}
								{#if (data.intake.response.answers[q.id] ?? []).length}
									<table class="iq-repeater">
										<thead><tr>{#each q.columns as col}<th>{col}</th>{/each}</tr></thead>
										<tbody>
											{#each data.intake.response.answers[q.id] as row}
												<tr>{#each q.columns as col}<td>{row[col] ?? '—'}</td>{/each}</tr>
											{/each}
										</tbody>
									</table>
								{:else}
									<div class="iq-value">—</div>
								{/if}
							{:else}
								<div class="iq-value">{formatAnswer(q, data.intake.response.answers[q.id])}</div>
							{/if}
						</li>
					{/each}
				</ul>
				{#if Object.keys(data.intake.notes ?? {}).length}
					<h3 class="iq-notes-h">Notes</h3>
					<ul class="list">
						{#each Object.entries(data.intake.notes) as [theme, note]}
							<li><strong>{theme}:</strong> {note}</li>
						{/each}
					</ul>
				{/if}
			</div>
		{:else}
			<p class="hint">No intake response yet.</p>
		{/if}
	{:else if active === 'intake'}
		<div class="rail-section"><h2>Intake Links</h2>
			<div class="link-actions">
				<Button variant="outlined" onclick={() => (showSendPicker = !showSendPicker)}>Send an intake form</Button>
				<Button variant="outlined" onclick={createUploadLink} loading={creatingUploadLink}>Get upload link</Button>
			</div>
			{#if showSendPicker}
				<div class="send-picker">
					{#if !followupQuestionnaires.length}
						<p class="hint">No follow-up intake forms yet — create one on the <a href="/practitioner/questionnaires">Intake</a> page first.</p>
					{:else}
						<Select label="Intake form" bind:value={selectedQuestionnaireId}
							options={followupQuestionnaires.map((q: any) => ({ value: q.id, label: q.title }))} />
						<Button onclick={sendQuestionnaire} loading={sendingQuestionnaire} disabled={!selectedQuestionnaireId}>Create link</Button>
					{/if}
				</div>
			{/if}
			{#if uploadLinkUrl}
				<p class="hint link-text">{uploadLinkUrl} <button type="button" class="copy-btn" onclick={copyUploadLink}>Copy</button></p>
			{/if}
			{#if !links.length}
				<p class="hint">No links sent yet.</p>
			{:else}
				<ul class="list doc-list">
					{#each links as l (l.token)}
						<li>
							{l.kind === 'upload' ? 'Upload link' : 'Intake link'}
							<span class="pill" class:final={l.status === 'submitted'}>{l.status === 'submitted' ? 'Submitted' : 'Open'}</span>
							<span class="hint">{l.created_at ?? ''}</span>
							{#if l.status !== 'submitted'}
								<button type="button" class="copy-btn" onclick={() => copyLinkUrl(l)}>Copy link</button>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	{:else if active === 'record'}
		<div class="rail-section">
			<form class="entry-form" onsubmit={addEntry}>
				<Select label="Kind" bind:value={entryKind} disabled={addingEntry}
					options={Object.entries(KIND_LABELS).filter(([v]) => v !== 'document').map(([value, label]) => ({ value, label }))} />
				<TextField label="Details" type="textarea" bind:value={entryContent} required disabled={addingEntry}
					placeholder="e.g. Fasting glucose 92 mg/dL, 2026-09-14" />
				<Button type="submit" loading={addingEntry}>Add to record</Button>
			</form>

			<label class="dropzone" class:drag-over={dragOver} use:fileDrop={handleFiles}
				ondragenter={() => (dragOver = true)} ondragleave={() => (dragOver = false)} ondrop={() => (dragOver = false)}>
				<Icon name="upload" size={18} />
				<span>{uploadingFile ? 'Uploading…' : 'Drag files here, or click to choose'}</span>
				<span class="hint">Labs, imaging, referrals, anything for this client — AI reads it, sorts it in below.</span>
				<input bind:this={fileInput} type="file" multiple onchange={onFilesPicked} disabled={uploadingFile} hidden />
			</label>
		</div>

		{#if !entries.length}
			<p class="hint">Nothing recorded yet — conditions, medications, labs, and documents added here shape what the consult pipeline considers when answering.</p>
		{:else}
			{#each CATEGORY_ORDER as cat}
				{#if groupedEntries[cat]?.length}
					<div class="rail-section category-section">
						<h2>{CATEGORY_LABELS[cat]}</h2>
						{#if cat === 'lab' && clinicalState.length}
							<ul class="list markers">
								{#each clinicalState as m (m.id)}
									<li class="marker">
										<span class="marker-name">{m.display_label}</span>
										<span class="marker-value">{m.value ?? '—'} {m.unit ?? ''}</span>
										<Chip tone={markerTone(m.flag)}>{m.flag === 'in_range' ? 'In range' : m.flag === 'unknown' ? 'Unflagged' : m.flag}</Chip>
										{#if m.trend}<span class="trend trend-{m.trend}">{trendArrow(m.trend)} {m.trend}</span>{/if}
									</li>
								{/each}
							</ul>
						{/if}
						<ul class="list entries">
							{#each groupedEntries[cat] as e (e.id)}
								<li class="entry">
									<div class="er">
										{#if e.file}
											<a href={fileUrl(e.file.id)} target="_blank" rel="noopener" class="entry-file-link">{e.file.original_name}</a>
											{#if e.file.ai_doc_type}
												<Chip tone="accent">{DOC_TYPE_LABELS[e.file.ai_doc_type] ?? e.file.ai_doc_type}</Chip>
											{:else}
												<Chip tone="neutral">Processing…</Chip>
											{/if}
										{:else}
											<Chip tone="neutral">{KIND_LABELS[e.kind] ?? e.kind}</Chip>
										{/if}
										{#if isClientReported(e.content)}<Chip tone="accent">Client-reported</Chip>{/if}
										<span class="hint">{e.created_at?.slice(0, 10)}</span>
										<button type="button" class="remove" onclick={() => removeEntry(e.id)} disabled={deletingEntry === e.id} title="Remove">×</button>
									</div>
									{#if e.file?.ai_summary}
										<p class="ai-summary">{e.file.ai_summary}</p>
									{:else}
										<p class="content">{entryText(e.content)}</p>
									{/if}
									{#if e.file?.ai_highlights?.length}
										<ul class="highlights">
											{#each e.file.ai_highlights as h}
												<li class="highlight highlight-{h.severity}">{h.text}</li>
											{/each}
										</ul>
									{/if}
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			{/each}
		{/if}
	{:else}
		<div class="rail-section"><h2>Sessions</h2>
			{#if !data.sessions?.length}
				<p class="hint">No consultation sessions yet.</p>
			{:else}
				<ul class="list">
					{#each data.sessions as s (s.id)}
						<li class="session">
							<div class="sr">
								<a href="/practitioner/consult?client={data.client.id}&session={s.id}">{s.title ?? s.last_question ?? s.id}</a>
								<Button variant="outlined" onclick={() => summarize(s.id)} loading={summarizing === s.id}>Summarize</Button>
							</div>
							{#if summaries[s.id]}<p class="summary">{summaries[s.id]}</p>{/if}
							{#if documentsBySession[s.id]?.length}
								<ul class="list doc-list session-docs">
									{#each documentsBySession[s.id] as d (d.id)}
										<li>
											<a href="/practitioner/consult?client={data.client.id}&session={d.session_id}&pane=doc&kind={d.kind}">
												{DOCUMENT_KIND_LABELS[d.kind] ?? d.kind}
											</a>
											<span class="pill" class:final={d.status === 'final'}>{d.status === 'final' ? 'Final' : 'Draft'}</span>
											{#if d.kind === 'client_report' && d.status === 'final'}
												<a class="pdf-link"
													href="{PUBLIC_API_BASE}/api/me/clients/{data.client.id}/sessions/{d.session_id}/documents/{d.kind}/pdf"
													target="_blank" rel="noopener">
													Download PDF
												</a>
											{/if}
										</li>
									{/each}
								</ul>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	{/if}
</div></div>

<style>
	.status-banner {
		display: flex; align-items: center; justify-content: space-between; gap: var(--space-4);
		margin-top: var(--space-4); padding: var(--space-4); border: 1px solid var(--line);
		border-radius: var(--r-lg); background: var(--accent-soft);
	}
	.status-label { font-weight: 700; color: var(--accent-ink); font-size: var(--text-base); }
	.status-detail { margin: .2rem 0 0; }
	.tabbar { margin: var(--space-4) 0; }
	.link-actions { display: flex; gap: var(--space-3); flex-wrap: wrap; margin-bottom: var(--space-3); }
	.send-picker {
		display: flex; align-items: flex-end; gap: var(--space-3); flex-wrap: wrap;
		padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--r); background: var(--panel-2);
		margin-bottom: var(--space-3);
	}
	.send-picker :global(.field) { flex: 1 1 14rem; }
	.rail-section { margin-bottom: var(--space-5); }
	.intake-panel { padding: var(--space-4); border: 1px solid var(--line); border-radius: var(--r-lg); background: var(--panel-2); margin-bottom: var(--space-5); }
	.intake-answers { margin-top: var(--space-3); }
	.intake-answer { padding: var(--space-2) 0; border-bottom: 1px solid var(--line); }
	.intake-answer:last-child { border-bottom: none; }
	.iq-prompt { font-weight: 650; font-size: var(--text-sm); }
	.iq-value { font-size: var(--text-sm); color: var(--ink-2); white-space: pre-wrap; }
	.iq-notes-h { font-size: var(--text-sm); font-weight: 650; letter-spacing: .04em; color: var(--muted); margin: var(--space-4) 0 var(--space-2); }
	.iq-repeater { width: 100%; border-collapse: collapse; margin-top: .3rem; font-size: var(--text-sm); }
	.iq-repeater th, .iq-repeater td { text-align: left; padding: .3rem .5rem; border-bottom: 1px solid var(--line); }
	.rail-section h2 { font-size: var(--text-sm); font-weight: 650; letter-spacing: .04em; color: var(--muted); margin-bottom: var(--space-2); }
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
	.doc-list li { display: flex; align-items: center; flex-wrap: wrap; gap: .5rem; }
	.doc-list a { font-weight: 600; }
	.doc-list .pill {
		display: inline-flex; padding: 1px 7px; border-radius: 99px; font-size: 10px; font-weight: 700;
		text-transform: uppercase; letter-spacing: .03em; background: var(--warn-soft); color: var(--warn);
	}
	.doc-list .pill.final { background: var(--accent-soft); color: var(--accent-ink); }
	.pdf-link { font-size: var(--text-xs); font-weight: 650; color: var(--accent-ink); text-decoration: none; }
	.pdf-link:hover { text-decoration: underline; }
	.link-text { word-break: break-all; display: flex; align-items: center; gap: .5rem; margin-top: var(--space-2); }
	.copy-btn { border: none; background: var(--panel-2); border-radius: var(--r); padding: .2rem .6rem; font-size: var(--text-xs); font-weight: 650; cursor: pointer; flex: none; }
	.dropzone {
		display: flex; flex-direction: column; align-items: center; gap: .3rem; text-align: center;
		border: 1px dashed var(--line-2); background: var(--panel-2); border-radius: var(--r-lg);
		padding: var(--space-5) var(--space-4); font-size: var(--text-sm); font-weight: 650; cursor: pointer;
		color: var(--ink-2); margin-bottom: var(--space-3); transition: border-color .15s, background .15s;
	}
	.dropzone:hover, .dropzone.drag-over { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-ink); }
	.dropzone .hint { font-weight: 400; max-width: 26rem; }
	.session { display: grid; gap: .35rem; }
	.session-docs { margin: .2rem 0 0 1rem; }
	.sr { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
	.summary { margin: 0; padding: var(--space-3); background: var(--panel-2); border-radius: var(--r); font-size: var(--text-sm); white-space: pre-wrap; }
	.entry-form { display: grid; gap: var(--space-3); }
	.entries { margin-top: var(--space-4); }
	.entry { padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--r); display: grid; gap: .3rem; }
	.er { display: flex; align-items: center; gap: .5rem; }
	.remove {
		margin-left: auto; border: none; background: none; color: var(--muted); cursor: pointer;
		font-size: 1.1rem; line-height: 1; padding: .1rem .3rem; border-radius: var(--r);
	}
	.remove:hover:not(:disabled) { background: var(--danger-soft); color: var(--danger); }
	.remove:disabled { opacity: .5; cursor: not-allowed; }
	.content { margin: 0; font-size: var(--text-sm); white-space: pre-wrap; }

	.category-section { padding-top: var(--space-3); border-top: 1px solid var(--line); }
	.entry-file-link { font-weight: 650; }
	.ai-summary { margin: 0; font-size: var(--text-sm); color: var(--ink-2); }
	.highlights { list-style: none; margin: .4rem 0 0; padding: 0; display: grid; gap: .3rem; }
	.highlight {
		font-size: var(--text-xs); padding: .3rem .6rem; border-radius: var(--r);
		background: var(--panel-2); color: var(--ink-2);
	}
	.highlight-flag { background: var(--danger-soft); color: var(--danger); font-weight: 600; }
	.highlight-info { background: var(--panel-2); color: var(--ink-2); }

	.markers { margin-bottom: var(--space-3); }
	.marker {
		display: flex; align-items: center; flex-wrap: wrap; gap: .5rem; padding: var(--space-2) var(--space-3);
		background: var(--panel-2); border-radius: var(--r); font-size: var(--text-sm);
	}
	.marker-name { font-weight: 650; }
	.marker-value { font-variant-numeric: tabular-nums; color: var(--ink-2); }
	.trend { font-size: var(--text-xs); font-weight: 650; color: var(--muted); }
	.trend-rising { color: var(--warn); }
	.trend-falling { color: var(--accent-ink); }
</style>
