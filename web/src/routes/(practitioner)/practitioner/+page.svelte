<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';
	import Button from '$lib/components/Button.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();
	const isPro = $derived(data.profile?.plan === 'pro');

	const steps = $derived([
		{ label: 'Add your first client', done: (data.clients?.length ?? 0) > 0, href: '/practitioner/clients' },
		{ label: 'Ask your first question in Consult', done: (data.recentSessions?.length ?? 0) > 0, href: '/practitioner/consult' }
	]);
	const showChecklist = $derived(isPro && !steps.every((s) => s.done));

	const tiles = $derived.by(() => {
		const intake = data.notifications?.unviewed_intake ?? 0;
		const newContacts = data.notifications?.new_contacts ?? 0;
		return [
			{ label: 'Consults logged', value: data.recentSessions?.length ?? 0, icon: 'message', href: '/practitioner/consult' },
			{ label: 'Clients', value: data.clients?.length ?? 0, icon: 'users', href: '/practitioner/clients' },
			{ label: 'Unviewed intake', value: intake, icon: 'clipboard', href: '/practitioner/clients', warn: intake > 0 },
			{ label: 'New contact submissions', value: newContacts, icon: 'mail', href: '/practitioner/contacts', warn: newContacts > 0 }
		];
	});

	const recentConsults = $derived((data.recentSessions ?? []).slice(0, 5));
</script>

<svelte:head><title>Overview — Practitioner portal</title></svelte:head>

<div class="pane-row">
	<div class="detail-pane">
		<div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="home" size={16} /></span><div><h1>Overview</h1><p>Welcome back.</p></div></div></div>

		{#if showChecklist}
			<div class="checklist">
				<span class="checklist-label">Getting started</span>
				{#each steps as s (s.label)}
					<a class="checklist-item" class:done={s.done} href={s.href}>
						<span class="mark" aria-hidden="true">{s.done ? '✓' : '○'}</span>{s.label}
					</a>
				{/each}
			</div>
		{/if}

		<div class="tile-grid">
			{#each tiles as t (t.label)}
				<StatTile label={t.label} value={t.value} icon={t.icon} href={t.href} tone={t.warn ? 'warn' : undefined} />
			{/each}
		</div>

		{#if isPro}
			<section class="block">
				<h2>Quick actions</h2>
				<div class="action-row">
					<Button variant="outlined" href="/practitioner/consult"><Icon name="message" size={15} />Start a consult</Button>
					<Button variant="outlined" href="/practitioner/clients"><Icon name="plus" size={15} />Add a client</Button>
					<Button variant="outlined" href="/practitioner/questionnaires"><Icon name="clipboard" size={15} />Edit questionnaires</Button>
				</div>
			</section>

			<section class="block">
				<div class="block-head">
					<h2>Recent consults</h2>
					<a class="see-all" href="/practitioner/consult">See all →</a>
				</div>
				{#if recentConsults.length}
					<ul class="consult-list">
						{#each recentConsults as s (s.id)}
							<li>
								<a href="/practitioner/consult?client={s.client_id}&session={s.id}">
									<span class="who">{s.client_name}</span>
									<span class="hint">{s.title ?? s.last_question ?? 'Untitled'}</span>
									<span class="when">{(s.started_at ?? '').slice(0, 16).replace('T', ' ')}</span>
								</a>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="hint">No consultations logged yet.</p>
				{/if}
			</section>
		{/if}
	</div>
</div>

<style>
	.checklist {
		display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap;
		border: 1px solid color-mix(in srgb, var(--accent) 25%, var(--line)); background: var(--accent-soft); border-radius: var(--r-lg);
		padding: var(--space-3) var(--space-4); margin-bottom: var(--space-5); font-size: var(--text-sm);
	}
	.checklist-label { font-weight: 650; color: var(--ink-2); }
	.checklist-item { display: flex; align-items: center; gap: .4rem; text-decoration: none; color: var(--ink); }
	.checklist-item.done { color: var(--muted); text-decoration: line-through; }
	.mark { font-weight: 700; }
	.tile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: var(--space-4); margin-bottom: var(--space-5); }
	.block { margin-bottom: var(--space-5); background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg); box-shadow: var(--shadow); padding: var(--space-4) var(--space-5); }
	.block-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); }
	.block h2, .block-head h2 { font-size: var(--text-base); font-weight: 650; margin-bottom: var(--space-3); }
	.see-all { font-size: var(--text-sm); font-weight: 600; color: var(--accent-ink); text-decoration: none; }
	.see-all:hover { text-decoration: underline; }
	.action-row { display: flex; flex-wrap: wrap; gap: var(--space-2); }
	.consult-list { list-style: none; margin: 0; padding: 0; display: grid; gap: .3rem; }
	.consult-list a {
		display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; font-size: var(--text-sm);
		padding: .6rem .5rem; margin: 0 -.5rem; border-radius: var(--r); text-decoration: none; color: var(--ink);
	}
	.consult-list a:hover { background: var(--panel-2); }
	.who { font-weight: var(--weight-medium); color: var(--ink-2); }
	.when { margin-left: auto; color: var(--muted); font-size: var(--text-xs); }
</style>
