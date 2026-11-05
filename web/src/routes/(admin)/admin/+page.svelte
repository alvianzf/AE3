<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();
	const s = $derived(data.stats ?? {});

	// Rail navigation reaches every section directly now — this page is
	// a quick read on the whole platform plus the handful of things an
	// admin actually comes here to check: what needs a decision (stat
	// tiles, warn-toned when non-zero), where to go next (quick actions),
	// and what just happened (recent activity) — not a menu of every
	// section again, the rail already is that.
	const tiles = $derived([
		{ label: 'Pending applications', value: s.pending_practitioners ?? 0, icon: 'users', href: '/admin/users?tab=practitioners', warn: (s.pending_practitioners ?? 0) > 0 },
		{ label: 'Approved practitioners', value: s.approved_practitioners ?? 0, icon: 'user-card', href: '/admin/users?tab=practitioners' },
		{ label: 'New contact submissions', value: s.new_contacts ?? 0, icon: 'mail', href: '/admin/users', warn: (s.new_contacts ?? 0) > 0 },
		{ label: 'Total profile views', value: s.total_views ?? 0, icon: 'eye' }
	]);

	const recent = $derived((data.audit ?? []).slice(0, 6));
	const latestDocs = $derived((data.latestDocs ?? []).slice(0, 6));
</script>

<svelte:head><title>Overview — Admin portal</title></svelte:head>

<div class="pane-row">
	<div class="detail-pane">
		<div class="detail-head"><div class="head-title"><span class="head-ico"><Icon name="home" size={16} /></span><div><h1>Overview</h1><p>A quick read on the whole platform.</p></div></div></div>

		<div class="tile-grid">
			{#each tiles as t (t.label)}
				<StatTile label={t.label} value={t.value} icon={t.icon} href={t.href} tone={t.warn ? 'warn' : undefined} />
			{/each}
		</div>

		<section class="block">
			<h2>Quick actions</h2>
			<div class="action-row">
				<Button variant="outlined" href="/admin/library"><Icon name="plus" size={15} />Add resources</Button>
				<Button variant="outlined" href="/admin/users?tab=practitioners"><Icon name="check" size={15} />Review practitioners</Button>
				<Button variant="outlined" href="/admin/questionnaires"><Icon name="clipboard" size={15} />Edit questionnaires</Button>
			</div>
		</section>

		<div class="cols-2">
			<section class="block">
				<div class="block-head">
					<h2>Recent activity</h2>
					<a class="see-all" href="/admin/audit">See all →</a>
				</div>
				{#if recent.length}
					<ul class="activity-list">
						{#each recent as a, i (a.ts + i)}
							<li>
								<Chip tone="neutral">{a.action}</Chip>
								<span class="who">{a.actor}</span>
								{#if a.detail}<span class="hint">{a.detail}</span>{/if}
								<span class="when">{(a.ts ?? '').slice(0, 16).replace('T', ' ')}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="hint">Nothing logged yet.</p>
				{/if}
			</section>

			<section class="block">
				<div class="block-head">
					<h2>Latest uploads</h2>
					<a class="see-all" href="/admin/library">See all →</a>
				</div>
				{#if latestDocs.length}
					<ul class="activity-list">
						{#each latestDocs as d (d.id)}
							<li>
								<a class="doc-link" href="/admin/{d.id}">{d.title}</a>
								<span class="when">{(d.created_at ?? '').slice(0, 10)}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="hint">Nothing uploaded yet.</p>
				{/if}
			</section>
		</div>
	</div>
</div>

<style>
	.tile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: var(--space-4); margin-bottom: var(--space-5); }
	.cols-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr)); gap: var(--space-4); align-items: start; }
	.cols-2 .block { margin-bottom: 0; }
	.block { margin-bottom: var(--space-5); background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg); box-shadow: var(--shadow); padding: var(--space-4) var(--space-5); }
	.block-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); }
	.block h2, .block-head h2 { font-size: var(--text-base); font-weight: 650; margin-bottom: var(--space-3); }
	.see-all { font-size: var(--text-sm); font-weight: 600; color: var(--accent-ink); text-decoration: none; }
	.see-all:hover { text-decoration: underline; }
	.action-row { display: flex; flex-wrap: wrap; gap: var(--space-2); }
	.activity-list { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
	.activity-list li {
		display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; font-size: var(--text-sm);
		padding: var(--space-2) 0; border-bottom: 1px solid var(--line);
	}
	.who { font-weight: var(--weight-medium); color: var(--ink-2); }
	.when { margin-left: auto; color: var(--muted); font-size: var(--text-xs); }
	.doc-link { color: var(--ink); text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.doc-link:hover { color: var(--accent-ink); }
</style>
