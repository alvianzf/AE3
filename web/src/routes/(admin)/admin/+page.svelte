<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();
	const s = $derived(data.stats ?? {});

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
		<div class="detail-head">
			<div class="head-title">
				<span class="head-ico"><Icon name="home" size={18} /></span>
				<div>
					<h1>Platform Overview</h1>
					<p>{(s.pending_practitioners ?? 0) > 0 ? `${s.pending_practitioners} practitioner application${s.pending_practitioners === 1 ? '' : 's'} awaiting review` : 'All systems and practitioner accounts operational'}</p>
				</div>
			</div>
			<div class="head-actions">
				<Button variant="filled" href="/admin/library"><Icon name="plus" size={14} />Add resources</Button>
				<Button variant="outlined" href="/admin/users?tab=practitioners"><Icon name="check" size={14} />Review practitioners</Button>
			</div>
		</div>

		<div class="tile-grid">
			{#each tiles as t (t.label)}
				<StatTile label={t.label} value={t.value} icon={t.icon} href={t.href} tone={t.warn ? 'warn' : undefined} />
			{/each}
		</div>

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
					<p class="hint empty-text">Nothing logged in audit history yet.</p>
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
								<span class="doc-ico"><Icon name="file" size={15} /></span>
								<a class="doc-link" href="/admin/{d.id}">{d.title}</a>
								<span class="when">{(d.created_at ?? '').slice(0, 10)}</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="hint empty-text">No library resources uploaded yet.</p>
				{/if}
			</section>
		</div>
	</div>
</div>

<style>
	.tile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: var(--space-4); margin-bottom: var(--space-5); }
	.cols-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(21rem, 1fr)); gap: var(--space-5); align-items: start; }
	.block {
		background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
		box-shadow: var(--shadow); padding: var(--space-5);
	}
	.block-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-4); }
	.block h2, .block-head h2 { font-size: 1.05rem; font-weight: 700; color: var(--ink); letter-spacing: -.01em; margin: 0; }
	.see-all { font-size: var(--text-sm); font-weight: 600; color: var(--accent-ink); text-decoration: none; }
	.see-all:hover { text-decoration: underline; }
	.empty-text { padding: var(--space-4) 0; text-align: center; color: var(--muted); }

	.activity-list { list-style: none; margin: 0; padding: 0; display: grid; gap: .4rem; }
	.activity-list li {
		display: flex; align-items: center; gap: .65rem; flex-wrap: wrap; font-size: var(--text-sm);
		padding: .5rem .65rem; border-radius: 8px; transition: background .12s var(--ease);
	}
	.activity-list li:hover { background: var(--panel-2); }
	.who { font-weight: 600; color: var(--ink); font-size: var(--text-sm); }
	.when { margin-left: auto; color: var(--muted); font-size: var(--text-xs); font-variant-numeric: tabular-nums; }
	.doc-ico { color: var(--muted); display: grid; place-items: center; }
	.doc-link { color: var(--ink); font-weight: 500; text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1 1 auto; }
	.doc-link:hover { color: var(--accent-ink); }
</style>
