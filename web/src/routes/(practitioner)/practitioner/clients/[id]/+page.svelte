<script lang="ts">
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { post, del } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Quiet from '$lib/components/Quiet.svelte';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Button from '$lib/components/Button.svelte';
	import Select from '$lib/components/Select.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();

	function fileUrl(f: any) {
		return `${PUBLIC_API_BASE}/api/me/clients/${data.client.id}/files/${f.id}`;
	}

	// The consult pipeline's patient context (app/patient/context.py) has
	// always read conditions/medications/labs — nothing ever wrote them
	// until now (found live, 2026-09-14: every real client's recent_labs
	// was empty because there was no way to record one, not because none
	// existed). This panel is that missing write path.
	const KIND_LABELS: Record<string, string> = {
		lab: 'Lab / test result', condition: 'Condition', medication: 'Medication',
		note: 'Note', history: 'History'
	};
	// A client can also add to their own record (POST /api/me/entries) —
	// self-reported entries carry this marker (app/main.py) so it's clear
	// here which ones a practitioner verified vs. what the patient said
	// themselves.
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

<Quiet title="Client overview">
	<p><strong>{data.client.name}</strong> — {data.client.email}</p>
	<p class="hint">{data.client.country ?? 'Country not set'} · DOB {data.client.dob ?? 'not set'}</p>
</Quiet>

<div class="rail-layout">
	<div class="rail">
		<Quiet title="Files">
			{#if !data.files?.length}
				<p class="hint">No files uploaded yet.</p>
			{:else}
				<ul class="list">
					{#each data.files as f (f.id)}
						<li><a href={fileUrl(f)} target="_blank" rel="noopener">{f.original_name}</a> <span class="hint">{f.uploaded_at ?? ''}</span></li>
					{/each}
				</ul>
			{/if}
		</Quiet>

		<Quiet title="Documents">
			{#if !data.documents?.length}
				<p class="hint">No documents yet.</p>
			{:else}
				<ul class="list">
					{#each data.documents as d (d.id)}<li>{d.filename ?? d.kind}</li>{/each}
				</ul>
			{/if}
		</Quiet>

		<Quiet title="Record">
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
		</Quiet>
	</div>

	<Spotlight title="Sessions">
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
	</Spotlight>
</div>

<style>
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
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
