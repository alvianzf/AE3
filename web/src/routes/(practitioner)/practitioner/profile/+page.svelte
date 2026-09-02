<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { put, post } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import Spotlight from '$lib/components/Spotlight.svelte';
	import Quiet from '$lib/components/Quiet.svelte';
	import TextField from '$lib/components/TextField.svelte';
	import Button from '$lib/components/Button.svelte';

	let { data } = $props();
	const p = $derived(data.profile);

	let name = $state('');
	let bio = $state('');
	let years_experience = $state('0');
	let saving = $state(false);

	// Seed the editable fields whenever the loaded profile changes (initial
	// load, or after invalidateAll() following a save) — not just once.
	$effect(() => {
		name = p?.name ?? '';
		bio = p?.bio ?? '';
		years_experience = String(p?.years_experience ?? 0);
	});

	let apiKey = $state('');
	let savingKey = $state(false);

	async function save(e: Event) {
		e.preventDefault();
		saving = true;
		try {
			await put(fetch, '/me/profile', { name, bio, years_experience: Number(years_experience) });
			toast('Profile updated.');
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			saving = false;
		}
	}

	async function saveKey(e: Event) {
		e.preventDefault();
		savingKey = true;
		try {
			await post(fetch, '/me/anthropic-key', { api_key: apiKey });
			toast('Anthropic key saved.');
			apiKey = '';
			await invalidateAll();
		} catch (err: any) {
			toast(err.message, 'alert');
		} finally {
			savingKey = false;
		}
	}
</script>

<svelte:head><title>Profile — Practitioner portal</title></svelte:head>

<Spotlight title="Your profile">
	<form onsubmit={save}>
		<TextField label="Name" bind:value={name} required />
		<TextField label="Bio" type="textarea" bind:value={bio} />
		<TextField label="Years of experience" type="number" bind:value={years_experience} />
		<Button type="submit" loading={saving}>Save</Button>
	</form>
</Spotlight>

<Quiet title="Anthropic API key">
	<p class="hint">{p?.has_anthropic_key ? 'A key is on file.' : 'No key on file yet — required to use Consult.'}</p>
	<form onsubmit={saveKey}>
		<TextField label="Anthropic API key" type="password" bind:value={apiKey} required />
		<Button type="submit" loading={savingKey}>Save key</Button>
	</form>
</Quiet>

<style>
	form { display: grid; gap: var(--space-3); margin-top: var(--space-2); }
</style>
