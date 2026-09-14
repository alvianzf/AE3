<script lang="ts">
	import { post, del } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Select from '$lib/components/Select.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';
	import Chip from '$lib/components/Chip.svelte';

	let { data } = $props();

	// Mirrors the practitioner-side panel (clients/[id]/+page.svelte) but
	// scoped to the client's own self-reported entries only — the backend
	// (GET /api/me/entries) already filters out anything a practitioner
	// wrote about them, so everything returned here is theirs.
	const KIND_LABELS: Record<string, string> = {
		lab: 'Lab / test result', condition: 'Condition', medication: 'Medication',
		note: 'Note', history: 'History'
	};
	const PREFIX = '[patient-reported] ';
	function entryText(content: string) {
		return content.startsWith(PREFIX) ? content.slice(PREFIX.length) : content;
	}

	let entries = $state<any[]>(data.entries ?? []);
	let entryKind = $state('lab');
	let entryContent = $state('');
	let adding = $state(false);
	let removing = $state<string | null>(null);

	async function addEntry(e: Event) {
		e.preventDefault();
		if (!entryContent.trim()) return;
		adding = true;
		try {
			const entry = await post(fetch, '/me/entries', { kind: entryKind, content: entryContent.trim() });
			entries = [entry, ...entries];
			entryContent = '';
			toast('Added to your record.');
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			adding = false;
		}
	}

	async function removeEntry(id: string) {
		removing = id;
		try {
			await del(fetch, `/me/entries/${id}`);
			entries = entries.filter((e) => e.id !== id);
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			removing = null;
		}
	}
</script>

<svelte:head><title>Health record — Client portal</title></svelte:head>

<Spotlight title="Your health record">
	<p class="hint">
		Add labs, conditions, medications, or anything else your practitioner should know about
		before your next consult. Your practitioner can see everything here; you can only remove
		what you added yourself.
	</p>

	<form class="entry-form" onsubmit={addEntry}>
		<Select label="Kind" bind:value={entryKind} disabled={adding}
			options={Object.entries(KIND_LABELS).map(([value, label]) => ({ value, label }))} />
		<TextField label="Details" type="textarea" bind:value={entryContent} required disabled={adding}
			placeholder="e.g. Fasting glucose 92 mg/dL, 2026-09-14" />
		<Button type="submit" loading={adding}>Add to my record</Button>
	</form>

	{#if entries.length}
		<ul class="list entries">
			{#each entries as e (e.id)}
				<li class="entry">
					<div class="er">
						<Chip tone="neutral">{KIND_LABELS[e.kind] ?? e.kind}</Chip>
						<span class="hint">{e.created_at?.slice(0, 10)}</span>
						<button type="button" class="remove" onclick={() => removeEntry(e.id)} disabled={removing === e.id} title="Remove">×</button>
					</div>
					<p class="content">{entryText(e.content)}</p>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="hint" style="margin-top: var(--space-4)">Nothing added yet.</p>
	{/if}
</Spotlight>

<style>
	.entry-form { display: grid; gap: var(--space-3); margin: var(--space-4) 0; }
	.list { list-style: none; margin: 0; padding: 0; display: grid; gap: .5rem; }
	.entry { padding: var(--space-3); border: 1px solid var(--line); border-radius: var(--r); display: grid; gap: .3rem; }
	.er { display: flex; align-items: center; gap: .5rem; }
	.remove {
		margin-left: auto; border: none; background: none; color: var(--muted); cursor: pointer;
		font-size: 1.1rem; line-height: 1; padding: .1rem .3rem; border-radius: var(--r);
	}
	.remove:hover:not(:disabled) { background: var(--danger-soft); color: var(--danger); }
	.remove:disabled { opacity: .5; cursor: not-allowed; }
	.content { margin: 0; font-size: var(--text-sm); white-space: pre-wrap; }
</style>
