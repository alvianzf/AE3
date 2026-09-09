<script lang="ts">
	import { PUBLIC_API_BASE } from '$env/static/public';
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Quiet from '$lib/components/Quiet.svelte';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();

	function fileUrl(f: any) {
		return `${PUBLIC_API_BASE}/api/me/clients/${data.client.id}/files/${f.id}`;
	}

	// POST .../summary has existed since v1 (app/llm.py's summarize_session())
	// but had no UI anywhere to reach it — specs/v4/04-known-issues.md#h6.
	let summarizing = $state<string | null>(null);
	let summaries = $state<Record<string, string>>({});

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

<style>
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
	.session { display: grid; gap: .35rem; }
	.sr { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
	.summary { margin: 0; padding: var(--space-3); background: var(--panel-2); border-radius: var(--r); font-size: var(--text-sm); white-space: pre-wrap; }
</style>
