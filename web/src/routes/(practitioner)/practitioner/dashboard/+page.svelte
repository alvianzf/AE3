<script lang="ts">
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import StatTile from '$lib/components/StatTile.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();

	// specs/v4.1/03 CR2 — step 1 was hardcoded `done: true` regardless of
	// data.clients, and step 2's condition (`unviewed_intake >= 0`) was true
	// for any non-negative number, i.e. always — neither step could ever
	// show as not done, so the checklist could never actually prompt a new
	// practitioner to do the thing it claims to track.
	const steps = $derived([
		{ label: 'Add your first client', done: (data.clients?.length ?? 0) > 0, href: '/practitioner/clients' },
		{ label: 'Set your Anthropic key', done: !!data.profile?.has_anthropic_key, href: '/practitioner/profile' },
		{ label: 'Ask your first question in Consult', done: (data.recentSessions?.length ?? 0) > 0, href: '/practitioner/consult' }
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
					{#if s.done}{s.label}{:else}<a href={s.href}>{s.label}</a>{/if}
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
	<StatTile label="New contacts" value={data.notifications.new_contacts ?? 0} icon="mail" href="/practitioner/contacts" />
	<StatTile label="Unviewed intake" value={data.notifications.unviewed_intake ?? 0} icon="clipboard" href="/practitioner/clients" />
	<StatTile label="Consults logged" value={data.recentSessions?.length ?? 0} icon="message" href="/practitioner/consult" />
</div>

<!-- specs/v4/03: history (actual work) promoted to Tier 1; recent contacts
     demoted to Tier 2 — visual weight, not spatial stacking. Side by side
     (rail-layout, app.css) instead of two full-width blocks in a row, same
     fix applied to /admin's Knowledge page. -->
<div class="rail-layout">
	<div class="rail">
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
	</div>

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
</div>

<style>
	.checklist { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
	.checklist li { display: flex; align-items: center; gap: .5rem; }
	.checklist li.done { color: var(--muted); text-decoration: line-through; }
	.mark { font-weight: 700; }
	.tiles { margin: var(--space-5) 0; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
	.list li { display: flex; align-items: center; justify-content: space-between; padding: var(--space-2) 0; border-bottom: 1px solid var(--line); }
</style>
