<script lang="ts">
	import { page } from '$app/state';
	import { streamConsult } from '$lib/consultStream';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import Select from '$lib/components/Select.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();
	let clientId = $state('');
	$effect(() => {
		if (!clientId) clientId = page.url.searchParams.get('client') ?? data.clients[0]?.id ?? '';
	});
	let question = $state('');
	let asking = $state(false);
	let steps = $state<{ agent: string; status: 'running' | 'done'; input_tokens?: number; output_tokens?: number }[]>([]);
	let result = $state<any>(null);

	const AGENT_LABELS: Record<string, string> = {
		librarian: 'Librarian', specialist: 'Specialist', checker: 'Checker'
	};

	async function ask(e: Event) {
		e.preventDefault();
		if (!clientId || !question.trim()) return;
		asking = true;
		steps = [];
		result = null;
		try {
			for await (const ev of streamConsult(clientId, question)) {
				if (ev.event === 'agent_start') {
					steps = [...steps, { agent: ev.agent, status: 'running' }];
				} else if (ev.event === 'agent_done') {
					steps = steps.map((s) =>
						s.agent === ev.agent && s.status === 'running'
							? { ...s, status: 'done', input_tokens: ev.input_tokens, output_tokens: ev.output_tokens }
							: s
					);
				} else if (ev.event === 'result') {
					result = ev;
				} else if (ev.event === 'error') {
					toast(ev.message, 'alert');
				}
			}
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			asking = false;
		}
	}
</script>

<svelte:head><title>Consult — Practitioner portal</title></svelte:head>

<div class="layout">
	<Quiet title="Client">
		<ul class="clientlist">
			{#each data.clients as c (c.id)}
				<li>
					<button class:on={clientId === c.id} onclick={() => (clientId = c.id)}>{c.name}</button>
				</li>
			{:else}
				<li class="hint">No clients yet.</li>
			{/each}
		</ul>
	</Quiet>

	<!-- Tier 1 + leafmark: the ask panel is the reason this page exists (specs/v4/03, kept from v3) -->
	<Spotlight title="Ask about this client" leaf>
		<form onsubmit={ask}>
			<Select label="Client" bind:value={clientId} options={data.clients.map((c: any) => ({ value: c.id, label: c.name }))} />
			<TextField label="Question" type="textarea" bind:value={question} required placeholder="What would you like to know?" />
			<Button type="submit" loading={asking}>Ask</Button>
		</form>

		{#if steps.length}
			<div class="progress">
				{#each steps as s (s.agent)}
					<div class="step" class:done={s.status === 'done'}>
						<span class="dot" aria-hidden="true"></span>
						{AGENT_LABELS[s.agent] ?? s.agent}
						{#if s.status === 'done'}
							<Chip tone="neutral">{s.input_tokens}→{s.output_tokens} tok</Chip>
						{:else}
							<span class="hint">running…</span>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		{#if result}
			<div class="result">
				<div class="rh">
					<Chip tone={result.verdict === 'pass' ? 'ok' : 'warn'}>{result.verdict}</Chip>
					{#if result.revised}<Chip tone="accent">revised</Chip>{/if}
				</div>
				<p>{result.answer}</p>
			</div>
		{/if}
	</Spotlight>
</div>

<style>
	.layout { display: grid; grid-template-columns: 16rem 1fr; gap: var(--space-5); align-items: start; }
	.clientlist { list-style: none; margin: 0; padding: 0; display: grid; gap: .25rem; }
	.clientlist button {
		width: 100%; text-align: left; border: none; background: none; padding: .5rem .6rem;
		border-radius: var(--r); cursor: pointer; font: inherit;
	}
	.clientlist button.on { background: var(--accent-soft); color: var(--accent-ink); font-weight: 650; }
	form { display: grid; gap: var(--space-3); }
	.progress { margin-top: var(--space-4); display: grid; gap: .4rem; }
	.step { display: flex; align-items: center; gap: .5rem; font-size: var(--text-sm); }
	.step .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--warn); animation: breathe 1s ease-in-out infinite; }
	.step.done .dot { background: var(--ok); animation: none; }
	.result { margin-top: var(--space-5); padding-top: var(--space-4); border-top: 1px solid var(--glass-line); }
	.rh { display: flex; gap: .5rem; margin-bottom: var(--space-2); }
	@media (max-width: 860px) { .layout { grid-template-columns: 1fr; } }
</style>
