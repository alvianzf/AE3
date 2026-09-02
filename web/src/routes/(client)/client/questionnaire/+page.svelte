<script lang="ts">
	import { post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	const q = $derived(data.questionnaire);

	let answers = $state<Record<string, string>>({});
	let submitting = $state(false);

	$effect(() => {
		answers = data.response?.answers ?? {};
	});

	async function submit(e: Event) {
		e.preventDefault();
		if (!q) return;
		submitting = true;
		try {
			await post(fetch, '/me/questionnaire', {
				questionnaire_id: q.id,
				questionnaire_version: q.version,
				answers
			});
			toast('Questionnaire submitted.');
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Questionnaire — Client portal</title></svelte:head>

<Spotlight title={q?.title ?? 'Questionnaire'}>
	{#if !q}
		<p class="hint">No questionnaire is active right now.</p>
	{:else}
		<form onsubmit={submit}>
			{#each q.questions as question (question.id)}
				<div class="field">
					<label for="q-{question.id}">{question.prompt}</label>
					<textarea id="q-{question.id}" bind:value={answers[question.id]} rows="3"></textarea>
				</div>
			{/each}
			<Button type="submit" loading={submitting}>Submit answers</Button>
		</form>
	{/if}
</Spotlight>

<style>
	form { display: grid; gap: var(--space-4); }
	.field { display: flex; flex-direction: column; gap: .35rem; }
	textarea {
		border: 1px solid var(--line-2); border-radius: var(--r); background: var(--panel);
		padding: var(--space-3); font: inherit;
	}
</style>
