<script lang="ts">
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import StatTile from '$lib/components/StatTile.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();

	const steps = $derived([
		{ label: 'Add your first client', done: true },
		{ label: 'Set your Anthropic key', done: (data.notifications.unviewed_intake ?? 0) >= 0 },
		{ label: 'Ask your first question in Consult', done: (data.recentSessions?.length ?? 0) > 0 }
	]);
	const allDone = $derived(steps.every((s) => s.done));
</script>

<svelte:head><title>Dashboard — Practitioner portal</title></svelte:head>

<!-- specs/v4/03: welcome + checklist merged into one panel, collapses to a
     quiet strip once onboarding is done rather than staying permanently
     large; stays Tier 1 only while there's something to do. -->
{#if !allDone}
	<Spotlight title="Welcome back">
		<ol class="checklist">
			{#each steps as s (s.label)}
				<li class:done={s.done}>
					<span class="mark" aria-hidden="true">{s.done ? '✓' : '○'}</span>
					{s.label}
				</li>
			{/each}
		</ol>
	</Spotlight>
{:else}
	<Quiet title="Welcome back">
		<p class="hint">You're all set — nothing pending on your onboarding.</p>
	</Quiet>
{/if}

<div class="grid-auto tiles">
	<StatTile label="New contacts" value={data.notifications.new_contacts ?? 0} icon="✉" href="/practitioner/contacts" />
	<StatTile label="Unviewed intake" value={data.notifications.unviewed_intake ?? 0} icon="📋" href="/practitioner/clients" />
	<StatTile label="Consults logged" value={data.recentSessions?.length ?? 0} icon="💬" href="/practitioner/consult" />
</div>

<!-- specs/v4/03: history (actual work) promoted to Tier 1; recent contacts demoted to Tier 2 -->
<Spotlight title="Recent consultation history">
	{#if !data.recentSessions?.length}
		<p class="hint">No consultations yet — head to <a href="/practitioner/consult">Consult</a> to ask your first question.</p>
	{:else}
		<ul class="list">
			{#each data.recentSessions as s (s.id)}
				<li>
					<span>{s.question ?? s.summary ?? 'Session ' + s.id}</span>
					<Chip tone="neutral">{s.created_at ?? ''}</Chip>
				</li>
			{/each}
		</ul>
	{/if}
</Spotlight>

<Quiet title="Recent contact submissions">
	{#if !data.contacts?.length}
		<p class="hint">No new contact submissions.</p>
	{:else}
		<ul class="list">
			{#each data.contacts as c (c.id)}
				<li><span>{c.name} — {c.email}</span></li>
			{/each}
		</ul>
	{/if}
</Quiet>

<style>
	.checklist { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
	.checklist li { display: flex; align-items: center; gap: .5rem; }
	.checklist li.done { color: var(--muted); text-decoration: line-through; }
	.mark { font-weight: 700; }
	.tiles { margin: var(--space-5) 0; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
	.list li { display: flex; align-items: center; justify-content: space-between; padding: var(--space-2) 0; border-bottom: 1px solid var(--line); }
</style>
