<script lang="ts">
	import HomeGrid, { type Tile } from '$lib/components/HomeGrid.svelte';

	let { data } = $props();
	const s = $derived(data.stats ?? {});
	const isSuperadmin = $derived(data.session?.admin_role === 'superadmin');

	// The whole of "where do I go" for the admin portal — one launcher,
	// no separate always-visible nav listing the same five destinations
	// on every single page. Each tile carries its own live status where
	// one exists, so "what needs attention" is readable from here alone.
	const tiles = $derived.by(() => {
		const t: Tile[] = [
			{
				href: '/admin/library', label: 'Library', icon: 'book', tone: 'accent',
				status: 'Upload, organize & browse'
			},
			{
				href: '/admin/users', label: 'Users', icon: 'users',
				tone: (s.pending_practitioners ?? 0) > 0 ? 'warn' : 'accent',
				status: (s.pending_practitioners ?? 0) > 0
					? `${s.pending_practitioners} application${s.pending_practitioners === 1 ? '' : 's'} pending`
					: `${s.approved_practitioners ?? 0} approved practitioners`
			},
			{
				href: '/admin/questionnaires', label: 'Questionnaires', icon: 'clipboard', tone: 'accent',
				status: 'Manage the default questionnaire'
			},
			{
				href: '/admin/audit', label: 'Audit history', icon: 'history', tone: 'accent',
				status: 'Library event log'
			}
		];
		if (isSuperadmin) {
			t.push({ href: '/admin/settings', label: 'Settings', icon: 'settings', tone: 'accent', status: 'AI provider & system health' });
		}
		return t;
	});
</script>

<svelte:head><title>Home — Admin portal</title></svelte:head>

<h1 class="page-title">Welcome back</h1>
<p class="page-sub">Pick where you're going.</p>

{#if (s.new_contacts ?? 0) > 0}
	<a class="attention" href="/admin/users">
		<strong>{s.new_contacts}</strong> new contact submission{s.new_contacts === 1 ? '' : 's'} →
	</a>
{/if}

<HomeGrid {tiles} />

<style>
	.page-title { font-size: var(--text-3xl); font-weight: var(--weight-bold); margin-bottom: .3rem; }
	.page-sub { color: var(--muted); margin-bottom: var(--space-5); }
	.attention {
		display: inline-flex; align-items: center; gap: .4rem; text-decoration: none; color: var(--ink);
		background: var(--warn-soft); border-radius: var(--r-lg); padding: var(--space-3) var(--space-4);
		font-size: var(--text-sm); margin-bottom: var(--space-5);
	}
	.attention strong { color: var(--warn); font-size: var(--text-lg); }
</style>
