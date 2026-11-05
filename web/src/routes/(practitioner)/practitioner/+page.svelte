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
			{ label: 'Active clients', value: data.clients?.length ?? 0, icon: 'users', href: '/practitioner/clients' },
			{ label: 'Unviewed intake', value: intake, icon: 'clipboard', href: '/practitioner/clients', warn: intake > 0 },
			{ label: 'New contacts', value: newContacts, icon: 'mail', href: '/practitioner/contacts', warn: newContacts > 0 }
		];
	});

	const firstName = $derived((data.profile?.name ?? data.session?.name ?? '').replace(/^Dr\.?\s+/i, '').split(/\s+/)[0]);
	const recentConsults = $derived((data.recentSessions ?? []).slice(0, 5));
</script>

<svelte:head><title>Overview — Practitioner portal</title></svelte:head>

<div class="pane-row">
	<div class="detail-pane">
		<div class="detail-head">
			<div class="head-title">
				<span class="head-ico"><Icon name="home" size={18} /></span>
				<div>
					<h1>{firstName ? `Welcome back, Dr. ${firstName}` : 'Practitioner Overview'}</h1>
					<p>{isPro ? 'Grounded clinical intelligence & client records' : 'Complete your profile to get started'}</p>
				</div>
			</div>
			<div class="head-actions">
				{#if isPro}
					<Button variant="filled" href="/practitioner/consult"><Icon name="message" size={15} />Start consult</Button>
					<Button variant="outlined" href="/practitioner/clients"><Icon name="plus" size={15} />Add client</Button>
				{:else}
					<Button variant="filled" href="/practitioner/profile"><Icon name="settings" size={15} />Open profile</Button>
				{/if}
			</div>
		</div>

		{#if showChecklist}
			<div class="checklist">
				<div class="checklist-badge"><Icon name="check" size={14} />Getting started</div>
				<div class="checklist-items">
					{#each steps as s (s.label)}
						<a class="checklist-item" class:done={s.done} href={s.href}>
							<span class="mark" aria-hidden="true">{s.done ? '✓' : '○'}</span>
							<span>{s.label}</span>
						</a>
					{/each}
				</div>
			</div>
		{/if}

		<div class="tile-grid">
			{#each tiles as t (t.label)}
				<StatTile label={t.label} value={t.value} icon={t.icon} href={t.href} tone={t.warn ? 'warn' : undefined} />
			{/each}
		</div>

		{#if isPro}
			<div class="cols-2">
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
										<span class="avatar-sm">{(s.client_name ?? '?').charAt(0)}</span>
										<div class="consult-info">
											<span class="who">{s.client_name}</span>
											<span class="hint">{s.title ?? s.last_question ?? 'Untitled session'}</span>
										</div>
										<span class="when">{(s.started_at ?? '').slice(0, 16).replace('T', ' ')}</span>
									</a>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="hint empty-text">No consultations logged yet. Start a consult to ground clinical inquiries.</p>
					{/if}
				</section>

				<section class="block">
					<div class="block-head">
						<h2>Clinical tools</h2>
					</div>
					<div class="tools-grid">
						<a class="tool-card" href="/practitioner/consult">
							<span class="tool-ico"><Icon name="message" size={18} /></span>
							<div class="tool-text">
								<strong>Clinical Consult</strong>
								<span>Ask grounded questions with multi-hop citations</span>
							</div>
						</a>
						<a class="tool-card" href="/practitioner/clients">
							<span class="tool-ico"><Icon name="users" size={18} /></span>
							<div class="tool-text">
								<strong>Client Vaults</strong>
								<span>Client conditions, labs, medications and intakes</span>
							</div>
						</a>
						<a class="tool-card" href="/practitioner/questionnaires">
							<span class="tool-ico"><Icon name="clipboard" size={18} /></span>
							<div class="tool-text">
								<strong>Questionnaires</strong>
								<span>Customize onboarding intake questionnaires</span>
							</div>
						</a>
						<a class="tool-card" href="/practitioner/knowledge">
							<span class="tool-ico"><Icon name="book" size={18} /></span>
							<div class="tool-text">
								<strong>Library Weights</strong>
								<span>Fine-tune knowledge base retrieval priorities</span>
							</div>
						</a>
					</div>
				</section>
			</div>
		{/if}
	</div>
</div>

<style>
	.checklist {
		display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap;
		border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--line)); background: var(--panel); border-radius: 14px;
		box-shadow: var(--shadow); padding: .75rem var(--space-5); margin-bottom: var(--space-5); font-size: var(--text-sm);
	}
	.checklist-badge {
		display: inline-flex; align-items: center; gap: .35rem; font-weight: 650; color: var(--accent-ink);
		background: var(--accent-soft); padding: .25rem .6rem; border-radius: 8px;
	}
	.checklist-items { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
	.checklist-item { display: flex; align-items: center; gap: .4rem; text-decoration: none; color: var(--ink); font-weight: 500; }
	.checklist-item.done { color: var(--muted); text-decoration: line-through; }
	.mark { font-weight: 700; color: var(--accent); }
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

	.consult-list { list-style: none; margin: 0; padding: 0; display: grid; gap: .4rem; }
	.consult-list li a {
		display: flex; align-items: center; gap: .75rem; padding: .65rem .75rem; border-radius: 10px;
		text-decoration: none; color: var(--ink); transition: background .12s var(--ease);
	}
	.consult-list li a:hover { background: var(--panel-2); }
	.avatar-sm {
		width: 2rem; height: 2rem; border-radius: 50%; display: grid; place-items: center;
		background: var(--accent-soft); color: var(--accent-ink); font-weight: 700; font-size: .75rem; flex: 0 0 auto;
	}
	.consult-info { display: flex; flex-direction: column; min-width: 0; flex: 1 1 auto; gap: .1rem; }
	.who { font-weight: 600; font-size: var(--text-sm); color: var(--ink); }
	.hint { font-size: var(--text-xs); color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.when { margin-left: auto; color: var(--muted); font-size: var(--text-xs); font-variant-numeric: tabular-nums; flex: 0 0 auto; }

	.tools-grid { display: grid; gap: .5rem; }
	.tool-card {
		display: flex; align-items: center; gap: .8rem; padding: .75rem .9rem; border-radius: 12px;
		border: 1px solid var(--line); background: var(--panel-2); text-decoration: none; color: inherit;
		transition: border-color .15s var(--ease), background .15s var(--ease), transform .15s var(--ease);
	}
	.tool-card:hover { border-color: var(--accent); background: var(--panel); transform: translateY(-1px); }
	.tool-ico {
		width: 2.25rem; height: 2.25rem; border-radius: 10px; display: grid; place-items: center;
		background: var(--accent-soft); color: var(--accent-ink); flex: 0 0 auto;
	}
	.tool-text { display: flex; flex-direction: column; gap: .15rem; min-width: 0; }
	.tool-text strong { font-size: var(--text-sm); font-weight: 650; color: var(--ink); }
	.tool-text span { font-size: var(--text-xs); color: var(--muted); }
</style>
