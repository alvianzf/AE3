<script lang="ts">
	import HomeGrid, { type Tile } from '$lib/components/HomeGrid.svelte';

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
		const t: Tile[] = [
			{
				href: '/practitioner/consult', label: 'Consult', icon: 'message', locked: !isPro,
				tone: 'accent', status: `${data.recentSessions?.length ?? 0} consults logged`
			},
			{
				href: '/practitioner/clients', label: 'Clients', icon: 'users', locked: !isPro,
				tone: intake > 0 ? 'warn' : 'accent',
				status: intake > 0 ? `${intake} unviewed intake` : `${data.clients?.length ?? 0} clients`
			},
			{
				href: '/practitioner/contacts', label: 'Contacts', icon: 'mail',
				tone: newContacts > 0 ? 'warn' : 'accent',
				status: newContacts > 0 ? `${newContacts} new` : 'No new submissions'
			},
			{ href: '/practitioner/knowledge', label: 'Library weights', icon: 'book', locked: !isPro, tone: 'accent', status: 'Tune what the AI draws from' },
			{ href: '/practitioner/questionnaires', label: 'Questionnaires', icon: 'clipboard', locked: !isPro, tone: 'accent', status: 'Manage intake forms' },
			{ href: '/practitioner/profile', label: 'Profile', icon: 'settings', tone: 'accent', status: 'Bio, photo & availability' },
			{ href: '/practitioner/upgrade', label: isPro ? 'Billing' : 'Upgrade', icon: 'star', tone: isPro ? 'accent' : 'warn', status: isPro ? 'Manage your plan' : 'Unlock Consult & Clients' }
		];
		return t;
	});
</script>

<svelte:head><title>Home — Practitioner portal</title></svelte:head>

<h1 class="page-title">Welcome back</h1>
<p class="page-sub">Pick where you're going.</p>

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

<HomeGrid {tiles} />

<style>
	.page-title { font-size: var(--text-3xl); font-weight: var(--weight-bold); margin-bottom: .3rem; }
	.page-sub { color: var(--muted); margin-bottom: var(--space-5); }
	.checklist {
		display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap;
		background: var(--panel-2); border: 1px solid var(--line); border-radius: var(--r-lg);
		padding: var(--space-3) var(--space-4); margin-bottom: var(--space-5); font-size: var(--text-sm);
	}
	.checklist-label { font-weight: 650; color: var(--ink-2); }
	.checklist-item { display: flex; align-items: center; gap: .4rem; text-decoration: none; color: var(--ink); }
	.checklist-item.done { color: var(--muted); text-decoration: line-through; }
	.mark { font-weight: 700; }
</style>
