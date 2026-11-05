<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();

	const items = $derived([
		{
			href: '/client/questionnaire', icon: 'clipboard',
			title: data.response ? 'Questionnaire submitted' : 'Intake questionnaire waiting',
			body: data.response ? 'Your practitioner has received your answers.' : 'Your practitioner uses this to understand your health history.',
			action: data.response ? 'Review answers' : 'Fill questionnaire', done: !!data.response
		},
		{
			href: '/client/record', icon: 'user-card',
			title: data.entries?.length ? `${data.entries.length} health record entries` : 'No health record entries yet',
			body: 'Only you and your practitioner can view your entries.',
			action: 'View record', done: !!data.entries?.length
		},
		{
			href: '/client/files', icon: 'folder',
			title: data.files?.length ? `${data.files.length} documents shared with you` : 'No documents shared yet',
			body: 'Clinical documents, protocols and lab reviews shared with you.',
			action: 'View files', done: !!data.files?.length
		}
	]);
</script>

<svelte:head><title>Home — Client portal</title></svelte:head>

<div class="pane-row">
	<div class="detail-pane">
		<div class="detail-head">
			<div class="head-title">
				<span class="head-ico"><Icon name="home" size={18} /></span>
				<div>
					<h1>{data.session?.name ? `Hello, ${data.session.name.split(' ')[0]}` : 'Your Care'}</h1>
					<p>Questionnaires, health records, and shared care documents</p>
				</div>
			</div>
		</div>

		<div class="stream">
			{#each items as it (it.href)}
				<a class="row" class:done={it.done} href={it.href}>
					<span class="ic" class:done={it.done}><Icon name={it.icon} size={20} /></span>
					<span class="body">
						<div class="title-row">
							<strong>{it.title}</strong>
							{#if it.done}
								<span class="status-pill ok">Completed</span>
							{:else}
								<span class="status-pill pending">Action needed</span>
							{/if}
						</div>
						<span class="hint">{it.body}</span>
					</span>
					<span class="action">{it.action} →</span>
				</a>
			{/each}
			<div class="row disabled-row">
				<span class="ic"><Icon name="watch" size={20} /></span>
				<span class="body">
					<div class="title-row">
						<strong>Connected Wearables</strong>
						<span class="status-pill neutral">Coming soon</span>
					</div>
					<span class="hint">Continuous glucose monitors, sleep trackers, and Oura integration.</span>
				</span>
				<span class="action muted">—</span>
			</div>
		</div>
	</div>
</div>

<style>
	.stream { display: grid; gap: var(--space-4); max-width: 52rem; }
	.row {
		display: flex; align-items: center; gap: var(--space-4); text-decoration: none; color: inherit;
		background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
		padding: var(--space-5); box-shadow: var(--shadow);
		transition: border-color .15s var(--ease), box-shadow .15s var(--ease), transform .15s var(--ease);
	}
	.row:hover:not(.disabled-row) {
		border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
		box-shadow: 0 6px 20px rgba(16, 24, 40, .07);
		transform: translateY(-1px);
	}
	.row.disabled-row { opacity: .75; cursor: default; background: var(--panel-2); }
	.ic {
		display: flex; align-items: center; justify-content: center; flex: 0 0 auto;
		width: 3rem; height: 3rem; border-radius: 12px; background: var(--accent-soft); color: var(--accent-ink);
	}
	.ic.done { background: var(--ok-soft); color: var(--ok); }
	.body { display: flex; flex-direction: column; gap: .3rem; flex: 1 1 auto; min-width: 0; }
	.title-row { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
	.body strong { font-size: 1.05rem; font-weight: 650; color: var(--ink); }
	.hint { font-size: var(--text-sm); color: var(--muted); }
	.status-pill {
		font-size: .68rem; font-weight: 700; padding: .15rem .5rem; border-radius: 99px;
		letter-spacing: .02em;
	}
	.status-pill.ok { background: var(--ok-soft); color: var(--ok); }
	.status-pill.pending { background: var(--accent-soft); color: var(--accent-ink); }
	.status-pill.neutral { background: var(--line); color: var(--muted); }
	.action {
		color: var(--accent-ink); font-size: var(--text-sm); font-weight: 650; white-space: nowrap;
		display: flex; align-items: center; gap: .25rem;
	}
	.action.muted { color: var(--muted); }
</style>
