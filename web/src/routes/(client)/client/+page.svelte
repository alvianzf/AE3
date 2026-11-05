<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();

	// specs/v8 §10.1 — "Your care" stream: a passive 4-tile grid ("here's
	// four menu items") becomes an ordered list of actual next actions, the
	// "what's next" answer this session's own research (§2.1) found every
	// dashboard in this app lacking, not just this one. Direct navigation
	// to each section still works from the rail — this page just stops
	// being a second copy of that same menu.
	const items = $derived([
		{
			href: '/client/questionnaire', icon: 'clipboard',
			title: data.response ? 'Questionnaire submitted' : 'Your questionnaire is waiting',
			body: data.response ? 'Your practitioner has your answers.' : 'Your practitioner uses this to understand your health history.',
			action: data.response ? 'Review' : 'Fill it in', done: !!data.response
		},
		{
			href: '/client/record', icon: 'user-card',
			title: data.entries?.length ? `${data.entries.length} health record entries` : 'No health record entries yet',
			body: 'Only you and your practitioner can see what’s here.',
			action: 'View', done: !!data.entries?.length
		},
		{
			href: '/client/files', icon: 'folder',
			title: data.files?.length ? `${data.files.length} files shared with you` : 'No files yet',
			body: 'Documents your practitioner has shared with you.',
			action: 'View', done: !!data.files?.length
		}
	]);
</script>

<svelte:head><title>Home — Client portal</title></svelte:head>

<!-- Wrapped in the same .pane-row/.detail-pane/.detail-head shell every
     other page in the app uses — this page previously had no wrapper at
     all, so it rendered with none of the shared padding/background/
     sticky-header treatment the rest of the portal gets. -->
<div class="pane-row">
	<div class="detail-pane">
		<div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="home" size={16} /></span><div><h1>Your care</h1><p>What's next, at a glance.</p></div></div></div>

		<div class="stream">
			{#each items as it (it.href)}
				<a class="row" class:done={it.done} href={it.href}>
					<span class="ic" class:done={it.done}><Icon name={it.icon} size={18} /></span>
					<span class="body">
						<strong>{it.title}</strong>
						<span class="hint">{it.body}</span>
					</span>
					<span class="action">{it.action} →</span>
				</a>
			{/each}
			<!-- specs/v6.6 — honest, never-optimistic state, unchanged: wearables
			     stays "Coming soon," not a fixture pretending to be live data. -->
			<a class="row" href="/client/wearables">
				<span class="ic"><Icon name="watch" size={18} /></span>
				<span class="body">
					<strong>Wearables</strong>
					<span class="hint">Coming soon.</span>
				</span>
				<span class="action">—</span>
			</a>
		</div>
	</div>
</div>

<style>
	.stream { display: grid; gap: var(--space-3); max-width: 36rem; }
	.row {
		display: flex; align-items: center; gap: var(--space-4); text-decoration: none; color: inherit;
		background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg);
		padding: var(--space-4); transition: border-color .15s var(--ease), transform .15s var(--ease);
	}
	.row:hover { border-color: var(--line-2); transform: translateX(2px); }
	.ic {
		display: flex; align-items: center; justify-content: center; flex: 0 0 auto;
		width: 2.6rem; height: 2.6rem; border-radius: 50%; background: var(--accent-soft); color: var(--accent-ink);
	}
	.ic.done { background: var(--ok-soft); color: var(--ok); }
	.body { display: flex; flex-direction: column; gap: .2rem; flex: 1 1 auto; min-width: 0; }
	.body strong { font-size: var(--text-base); }
	.action { color: var(--accent-ink); font-size: var(--text-sm); font-weight: 650; white-space: nowrap; }
</style>
