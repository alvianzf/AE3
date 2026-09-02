<script lang="ts">
	import Quiet from '$lib/components/Quiet.svelte';
	import Spotlight from '$lib/components/Spotlight.svelte';

	let { data } = $props();
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
				<li><a href="/practitioner/consult?client={data.client.id}&session={s.id}">{s.question ?? s.id}</a></li>
			{/each}
		</ul>
	{/if}
</Spotlight>

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
</style>
