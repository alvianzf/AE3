<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import StatTile from '$lib/components/StatTile.svelte';
	import Toggle from '$lib/components/Toggle.svelte';
	import Button from '$lib/components/Button.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let { data } = $props();
	const s = $derived(data.stats ?? {});
	const isSuperadmin = $derived(data.session?.admin_role === 'superadmin');
	let switchingProvider = $state(false);
	// Optimistic-ish: reflects the last load's value, then whatever the
	// toggle just set — invalidateAll() below re-syncs it from the server.
	let llmProvider = $state(data.llmProvider);
	$effect(() => { llmProvider = data.llmProvider; });

	// Role.EMBEDDER always stays on Nebius regardless of this setting —
	// Anthropic has no embeddings endpoint (app/clients/llm_client.py) —
	// so the toggle only covers the other five chat-model roles.
	async function setProvider(useAnthropic: boolean) {
		const provider = useAnthropic ? 'anthropic' : 'nebius';
		switchingProvider = true;
		try {
			await post(fetch, '/superadmin/llm-provider', { provider });
			llmProvider = provider;
			toast(`AI team switched to ${provider === 'anthropic' ? 'Anthropic (Opus/Sonnet/Haiku)' : 'Nebius'}.`);
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			switchingProvider = false;
		}
	}
	// Fields site_stats() (app/core_store.py) doesn't have a dedicated tile
	// for below — rendered generically so a future stat added there doesn't
	// need a matching frontend change to show up somewhere.
	const KNOWN_STATS = new Set([
		'total_views', 'total_contacts', 'new_contacts',
		'pending_practitioners', 'approved_practitioners',
	]);
	const otherStats = $derived(Object.entries(s).filter(([k]) => !KNOWN_STATS.has(k)));
</script>

<svelte:head><title>Dashboard — Admin portal</title></svelte:head>

<div class="page-head">
	<div>
		<h1>Dashboard</h1>
		<p>A quick read on the whole platform.</p>
	</div>
	<Button href="/admin/library"><Icon name="book" size={15} /> Go to Library</Button>
</div>

<!-- specs/v8 §6 Dashboard/Overview template — "needs your attention" comes
     first, above the passive at-a-glance grid below it, not buried inside
     a tile among equally-weighted stats an admin has to read past. -->
{#if (s.pending_practitioners ?? 0) > 0 || (s.new_contacts ?? 0) > 0}
	<div class="attention">
		<h2 class="section-title">Needs your attention</h2>
		<div class="attention-row">
			{#if (s.pending_practitioners ?? 0) > 0}
				<a class="attention-item" href="/admin/users">
					<strong>{s.pending_practitioners}</strong> practitioner application{s.pending_practitioners === 1 ? '' : 's'} pending review
				</a>
			{/if}
			{#if (s.new_contacts ?? 0) > 0}
				<a class="attention-item" href="/admin/users">
					<strong>{s.new_contacts}</strong> new contact submission{s.new_contacts === 1 ? '' : 's'}
				</a>
			{/if}
		</div>
	</div>
{/if}

<h2 class="section-title">At a glance</h2>
<div class="grid-auto tiles">
	<StatTile
		label="Pending applications"
		value={s.pending_practitioners ?? 0}
		icon="clipboard"
		href="/admin/users"
	/>
	<StatTile
		label="Approved practitioners"
		value={s.approved_practitioners ?? 0}
		icon="users"
		href="/admin/users"
	/>
	<StatTile
		label="New contact submissions"
		value={s.new_contacts ?? 0}
		icon="mail"
		href="/admin/users"
	/>
	<StatTile
		label="Total profile views"
		value={s.total_views ?? 0}
		icon="eye"
	/>
	{#each otherStats as [key, value] (key)}
		<StatTile label={key.replaceAll('_', ' ')} value={String(value)} />
	{/each}
</div>

{#if isSuperadmin}
	<h2 class="section-title">AI model provider</h2>
	<p class="hint">
		Switches Reader, Graph-builder, Answer-engine, Reasoner and Checker-LLM between
		Nebius and Anthropic (Opus 5 / Sonnet 5 / Haiku 4.5). Embedder always stays on
		Nebius — Anthropic has no embeddings endpoint.
	</p>
	<div class="check-row provider-row">
		<Toggle
			checked={llmProvider === 'anthropic'}
			onchange={setProvider}
			disabled={switchingProvider}
			label="Use Anthropic for the AI team's chat roles"
		/>
		<span class="hint">{llmProvider === 'anthropic' ? 'Anthropic' : 'Nebius'}</span>
	</div>
{/if}

<style>
	.tiles { margin-top: var(--space-5); }
	.section-title { margin-top: var(--space-6); margin-bottom: var(--space-2); font-size: var(--text-base); }
	.attention { margin-top: var(--space-4); }
	.attention-row { display: flex; flex-wrap: wrap; gap: var(--space-3); }
	.attention-item {
		display: flex; align-items: center; gap: .4rem; text-decoration: none; color: var(--ink);
		background: var(--warn-soft); border: 1px solid var(--line); border-radius: var(--r-lg);
		padding: var(--space-3) var(--space-4); font-size: var(--text-sm);
	}
	.attention-item strong { color: var(--warn); font-size: var(--text-lg); }
	.attention-item:hover { border-color: var(--line-2); }
	.check-row { display: flex; align-items: center; gap: .5rem; }
	.provider-row { margin-top: var(--space-3); }
</style>
