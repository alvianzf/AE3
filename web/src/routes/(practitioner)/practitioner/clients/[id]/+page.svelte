<script lang="ts">
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { post, del } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Icon from '$lib/components/Icon.svelte';
	import Button from '$lib/components/Button.svelte';
	import Select from '$lib/components/Select.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();

	function fileUrl(f: any) {
		return `${PUBLIC_API_BASE}/api/me/clients/${data.client.id}/files/${f.id}`;
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

	// session_documents rows have no `filename` — this list used to fall
	// back to the raw `kind` string. The Consult Draft Editor makes these
	// rows real and user-facing, so the fallback is replaced outright
	// with a proper label, a draft/final pill, and a deep link back into
	// the document pane that produced it.
	const DOCUMENT_KIND_LABELS: Record<string, string> = {
		clinician_note: 'Clinician Note',
		client_report: 'Client Report'
	};

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
		history: 'History'
	};
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
	function isPatientReported(content: string) {
		return content.startsWith(PATIENT_REPORTED_PREFIX);
	}
	let entries = $state<any[]>(data.entries ?? []);
	let entryKind = $state('lab');
	let entryContent = $state('');
	let addingEntry = $state(false);
	let deletingEntry = $state<string | null>(null);

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

	{#if data.intake?.response}
		<div class="rail-section intake-panel">
			<h2>Questionnaire Response</h2>
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
	{/if}

	<div class="rail-layout">
		<div class="rail">
			<div class="rail-section"><h2>Intake Links</h2>
				<Button variant="outlined" onclick={createUploadLink} loading={creatingUploadLink}>Get upload link</Button>
				{#if uploadLinkUrl}
					<p class="hint link-text">{uploadLinkUrl} <button type="button" class="copy-btn" onclick={copyUploadLink}>Copy</button></p>
				{/if}
				{#if !data.links?.length}
					<p class="hint">No links sent yet.</p>
				{:else}
					<ul class="list doc-list">
						{#each data.links as l (l.token)}
							<li>
								{l.kind === 'upload' ? 'Upload link' : 'Questionnaire link'}
								<span class="pill" class:final={l.status === 'submitted'}>{l.status === 'submitted' ? 'Submitted' : 'Open'}</span>
								<span class="hint">{l.created_at ?? ''}</span>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="rail-section"><h2>Files</h2>
				{#if !data.files?.length}
					<p class="hint">No files uploaded yet.</p>
				{:else}
					<ul class="list">
						{#each data.files as f (f.id)}
							<li><a href={fileUrl(f)} target="_blank" rel="noopener">{f.original_name}</a> <span class="hint">{f.uploaded_at ?? ''}</span></li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="rail-section"><h2>Documents</h2>
				{#if !data.documents?.length}
					<p class="hint">No documents yet.</p>
				{:else}
					<ul class="list doc-list">
						{#each data.documents as d (d.id)}
							<li>
								<a href="/practitioner/consult?client={data.client.id}&session={d.session_id}&pane=doc&kind={d.kind}">
									{DOCUMENT_KIND_LABELS[d.kind] ?? d.kind}
								</a>
								<span class="pill" class:final={d.status === 'final'}>{d.status === 'final' ? 'Final' : 'Draft'}</span>
								<span class="hint">{d.session_title ?? ''} · {d.updated_at ?? ''}</span>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			<div class="rail-section"><h2>Record</h2>
				<form class="entry-form" onsubmit={addEntry}>
					<Select label="Kind" bind:value={entryKind} disabled={addingEntry}
						options={Object.entries(KIND_LABELS).map(([value, label]) => ({ value, label }))} />
					<TextField label="Details" type="textarea" bind:value={entryContent} required disabled={addingEntry}
						placeholder="e.g. Fasting glucose 92 mg/dL, 2026-09-14" />
					<Button type="submit" loading={addingEntry}>Add to record</Button>
				</form>

				{#if entries.length}
					<ul class="list entries">
						{#each entries as e (e.id)}
							<li class="entry">
								<div class="er">
									<Chip tone="neutral">{KIND_LABELS[e.kind] ?? e.kind}</Chip>
									{#if isPatientReported(e.content)}<Chip tone="accent">Patient-reported</Chip>{/if}
									<span class="hint">{e.created_at?.slice(0, 10)}</span>
									<button type="button" class="remove" onclick={() => removeEntry(e.id)} disabled={deletingEntry === e.id} title="Remove">×</button>
								</div>
								<p class="content">{entryText(e.content)}</p>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="hint" style="margin-top: var(--space-3)">Nothing recorded yet — conditions, medications, and labs added here shape what the consult pipeline considers when answering.</p>
				{/if}
			</div>
		</div>

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
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</div>
</div></div>

<style>
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
	.link-text { word-break: break-all; display: flex; align-items: center; gap: .5rem; margin-top: var(--space-2); }
	.copy-btn { border: none; background: var(--panel-2); border-radius: var(--r); padding: .2rem .6rem; font-size: var(--text-xs); font-weight: 650; cursor: pointer; flex: none; }
	.session { display: grid; gap: .35rem; }
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
</style>
